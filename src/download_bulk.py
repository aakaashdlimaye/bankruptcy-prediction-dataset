"""Download the SEC bulk files once, into data/raw/, with resume + size check.

These are big (companyfacts ~1.4 GB, submissions ~1.6 GB) so they are fetched
in one pass rather than via thousands of per-company API calls, per the spec's
"prefer bulk files" rule. Re-running is a no-op once the files are complete.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C
import sec_client as sec

COMPANYFACTS_ZIP = C.RAW / "companyfacts.zip"
SUBMISSIONS_ZIP = C.RAW / "submissions.zip"
TICKERS_JSON = C.RAW / "company_tickers.json"


def main(what: str = "all") -> None:
    manifest_path = C.RAW / "bulk_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    jobs = []
    if what in ("all", "tickers"):
        jobs.append(("company_tickers.json", C.COMPANY_TICKERS_URL, TICKERS_JSON, 10_000))
    if what in ("all", "submissions"):
        jobs.append(("submissions.zip", C.BULK_SUBMISSIONS_URL, SUBMISSIONS_ZIP, 100_000_000))
    if what in ("all", "companyfacts"):
        jobs.append(("companyfacts.zip", C.BULK_COMPANYFACTS_URL, COMPANYFACTS_ZIP, 100_000_000))

    for name, url, dest, min_bytes in jobs:
        print(f"[download] {name}")
        sec.download_file(url, dest, min_bytes=min_bytes)
        manifest[name] = {
            "url": url,
            "bytes": dest.stat().st_size,
            "sha256_first_64mb": sec.sha256_of(dest, limit_mb=64),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"[download] {name} ok ({dest.stat().st_size / 1e6:.1f} MB)")

    print("[download] all bulk files present")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="all",
                    choices=["all", "tickers", "submissions", "companyfacts"])
    main(**vars(ap.parse_args()))
