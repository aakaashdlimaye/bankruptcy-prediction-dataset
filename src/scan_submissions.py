"""Single pass over data/raw/submissions.zip.

The archive holds one JSON per CIK (plus overflow shards for long filing
histories). One sequential pass yields everything two later phases need:

  * data/interim/company_meta.parquet      - cik, name, SIC, tickers, exchanges,
                                             10-K/10-Q counts inside the study
                                             window, first/last filing dates
  * data/interim/submissions_8k_item103.csv - every 8-K reporting item 1.03,
                                             from the authoritative `items`
                                             field (Phase 1 source B)

Checkpointed: if either output exists and --force is not given, it is reused.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from tqdm import tqdm

import config as C

ZIP_PATH = C.RAW / "submissions.zip"
META_OUT = C.INTERIM / "company_meta.parquet"
ITEM103_OUT = C.INTERIM / "submissions_8k_item103.csv"

MAIN_RE = re.compile(r"^CIK(\d{10})\.json$")
SHARD_RE = re.compile(r"^CIK(\d{10})-submissions-\d+\.json$")

WIN_LO, WIN_HI = C.STUDY_START, C.STUDY_END
PERIODIC = ("10-K", "10-Q")


def _blank_agg() -> dict:
    return {"n_10k": 0, "n_10q": 0, "n_10k_win": 0, "n_10q_win": 0,
            "first_filing": None, "last_filing": None,
            "first_period": None, "last_period": None}


def _scan_chunk(chunk: dict, cik: str, agg: dict, items103: list,
                meta: dict) -> None:
    forms = chunk.get("form") or []
    if not forms:
        return
    fdates = chunk.get("filingDate") or []
    rdates = chunk.get("reportDate") or []
    items = chunk.get("items") or []
    accns = chunk.get("accessionNumber") or []
    n = len(forms)

    for i in range(n):
        form = forms[i]
        fd = fdates[i] if i < len(fdates) else ""
        if not form:
            continue

        if form.startswith("8-K"):
            it = items[i] if i < len(items) else ""
            if it and "1.03" in str(it):
                items103.append({
                    "cik": cik,
                    "company": meta.get("name", ""),
                    "file_date": fd,
                    "form": form,
                    "accession": accns[i] if i < len(accns) else "",
                    "sic": meta.get("sic"),
                    "items": it,
                    "is_primary_filer": 1,
                })
            continue

        base = form.split("/")[0]
        if base not in ("10-K", "10-Q", "10-KT", "10-QT"):
            continue
        rd = rdates[i] if i < len(rdates) else ""
        is_k = base.startswith("10-K")
        if is_k:
            agg["n_10k"] += 1
        else:
            agg["n_10q"] += 1
        if rd and WIN_LO <= rd <= WIN_HI:
            if is_k:
                agg["n_10k_win"] += 1
            else:
                agg["n_10q_win"] += 1
        if fd:
            if agg["first_filing"] is None or fd < agg["first_filing"]:
                agg["first_filing"] = fd
            if agg["last_filing"] is None or fd > agg["last_filing"]:
                agg["last_filing"] = fd
        if rd:
            if agg["first_period"] is None or rd < agg["first_period"]:
                agg["first_period"] = rd
            if agg["last_period"] is None or rd > agg["last_period"]:
                agg["last_period"] = rd


def main(force: bool = False) -> None:
    if META_OUT.exists() and ITEM103_OUT.exists() and not force:
        print(f"[scan] cached -> {META_OUT.name}, {ITEM103_OUT.name}")
        return
    if not ZIP_PATH.exists():
        raise SystemExit(f"missing {ZIP_PATH}; run src/download_bulk.py first")

    metas: dict[str, dict] = {}
    aggs: dict[str, dict] = defaultdict(_blank_agg)
    items103: list[dict] = []

    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        print(f"[scan] {len(names):,} entries in submissions.zip")

        # Pass 1: main files carry the company metadata + recent filings.
        mains = [n for n in names if MAIN_RE.match(n)]
        shards = [n for n in names if SHARD_RE.match(n)]
        print(f"[scan] {len(mains):,} company files, {len(shards):,} history shards")

        for name in tqdm(mains, unit="co", mininterval=5.0, desc="companies"):
            try:
                blob = json.loads(zf.read(name))
            except Exception:                                # noqa: BLE001
                continue
            cik = str(int(MAIN_RE.match(name).group(1)))
            sic = blob.get("sic")
            try:
                sic_i = int(sic) if sic not in (None, "", "0000") else None
            except (TypeError, ValueError):
                sic_i = None
            meta = {
                "cik": cik,
                "name": (blob.get("name") or "").strip(),
                "sic": sic_i,
                "sic_desc": blob.get("sicDescription") or "",
                "tickers": ",".join(blob.get("tickers") or []),
                "exchanges": ",".join([e for e in (blob.get("exchanges") or []) if e]),
                "state_inc": blob.get("stateOfIncorporation") or "",
                "entity_type": blob.get("entityType") or "",
            }
            metas[cik] = meta
            filings = blob.get("filings") or {}
            _scan_chunk(filings.get("recent") or {}, cik, aggs[cik], items103, meta)

        # Pass 2: overflow shards (older filings for prolific filers).
        for name in tqdm(shards, unit="shard", mininterval=5.0, desc="history"):
            m = SHARD_RE.match(name)
            cik = str(int(m.group(1)))
            try:
                chunk = json.loads(zf.read(name))
            except Exception:                                # noqa: BLE001
                continue
            _scan_chunk(chunk, cik, aggs[cik], items103, metas.get(cik, {}))

    rows = []
    for cik, meta in metas.items():
        a = aggs.get(cik) or _blank_agg()
        rows.append({**meta, **a})
    meta_df = pd.DataFrame(rows)
    meta_df["has_periodic_in_window"] = (
        (meta_df["n_10k_win"] + meta_df["n_10q_win"]) > 0).astype(int)
    meta_df.to_parquet(META_OUT, index=False)
    print(f"[scan] wrote {len(meta_df):,} companies -> {META_OUT.name}")

    it_df = pd.DataFrame(items103).drop_duplicates(subset=["cik", "accession"])
    it_df.to_csv(ITEM103_OUT, index=False)
    print(f"[scan] wrote {len(it_df):,} item-1.03 8-K filings "
          f"({it_df['cik'].nunique():,} CIKs) -> {ITEM103_OUT.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    main(**vars(ap.parse_args()))
