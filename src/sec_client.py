"""Rate-limited, cached, resumable HTTP client for sec.gov / data.sec.gov.

Etiquette enforced here so no other module can accidentally violate it:
  * every request carries the required descriptive User-Agent
  * a token-bucket limiter keeps us under SEC_MAX_RPS (< the 10/s ceiling)
  * retries with exponential backoff on 429/5xx
  * big files download to `<name>.part` and resume via HTTP Range
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

import requests

from config import (CACHE, SEC_MAX_RPS, SEC_RETRIES, SEC_TIMEOUT, USER_AGENT)

_LOCK = threading.Lock()
_LAST_CALL = [0.0]
_MIN_INTERVAL = 1.0 / SEC_MAX_RPS


def _throttle() -> None:
    with _LOCK:
        wait = _MIN_INTERVAL - (time.monotonic() - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.monotonic()


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": None,  # set per-request by requests
    })
    s.headers.pop("Host", None)
    return s


SESSION = _session()


def get(url: str, *, params: dict | None = None, stream: bool = False,
        headers: dict | None = None, retries: int = SEC_RETRIES):
    """GET with throttling + backoff. Raises on final failure."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        _throttle()
        try:
            r = SESSION.get(url, params=params, stream=stream,
                            timeout=SEC_TIMEOUT, headers=headers or {})
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code} for {r.url}")
            r.raise_for_status()
            return r
        except Exception as exc:                      # noqa: BLE001
            last_exc = exc
            sleep = min(60.0, (2 ** attempt) * 1.5)
            print(f"    [retry {attempt + 1}/{retries}] {exc} -> sleeping {sleep:.1f}s")
            time.sleep(sleep)
    raise RuntimeError(f"GET failed after {retries} attempts: {url}") from last_exc


def get_json(url: str, *, params: dict | None = None, cache_key: str | None = None,
             cache_ttl_days: float | None = None):
    """GET JSON with an on-disk cache so re-runs never re-hit the SEC."""
    if cache_key is None:
        raw = url + json.dumps(params or {}, sort_keys=True)
        cache_key = hashlib.sha256(raw.encode()).hexdigest()[:24]
    path = CACHE / f"{cache_key}.json"
    if path.exists() and path.stat().st_size > 0:
        if cache_ttl_days is None or (time.time() - path.stat().st_mtime) < cache_ttl_days * 86400:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                path.unlink(missing_ok=True)
    data = get(url, params=params).json()
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def download_file(url: str, dest: Path, *, min_bytes: int = 1024,
                  force: bool = False) -> Path:
    """Resumable download with a size sanity check. Skips if already complete."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")

    # Ask the server how big the file is (also validates the URL).
    _throttle()
    head = SESSION.head(url, timeout=SEC_TIMEOUT, allow_redirects=True)
    remote_size = int(head.headers.get("Content-Length", 0) or 0)

    if dest.exists() and not force:
        local = dest.stat().st_size
        if local >= min_bytes and (remote_size == 0 or local == remote_size):
            print(f"  cached: {dest.name} ({local / 1e6:.1f} MB)")
            return dest
        print(f"  size mismatch for {dest.name} "
              f"(local {local}, remote {remote_size}) -> re-downloading")
        dest.unlink()

    start = part.stat().st_size if part.exists() else 0
    mode = "ab" if start else "wb"
    headers = {"Range": f"bytes={start}-"} if start else {}
    if start:
        print(f"  resuming {dest.name} at {start / 1e6:.1f} MB")

    _throttle()
    with SESSION.get(url, stream=True, timeout=SEC_TIMEOUT, headers=headers) as r:
        r.raise_for_status()
        total = remote_size or int(r.headers.get("Content-Length", 0) or 0) + start
        done = start
        tick = time.time()
        with open(part, mode) as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if time.time() - tick > 15:
                    pct = f"{100 * done / total:.1f}%" if total else "?"
                    print(f"    {dest.name}: {done / 1e6:.0f} MB ({pct})", flush=True)
                    tick = time.time()

    if done < min_bytes:
        raise RuntimeError(f"{dest.name} too small ({done} bytes) - download failed")
    part.replace(dest)
    print(f"  downloaded: {dest.name} ({done / 1e6:.1f} MB)")
    return dest


def sha256_of(path: Path, limit_mb: int | None = None) -> str:
    h = hashlib.sha256()
    budget = None if limit_mb is None else limit_mb * (1 << 20)
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1 << 20)
            if not block:
                break
            h.update(block)
            if budget is not None:
                budget -= len(block)
                if budget <= 0:
                    break
    return h.hexdigest()
