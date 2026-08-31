"""Phase 6 - Supplementary pre-labelled bankruptcy datasets.

Three external sets, used for ratio-family validation and cross-market
robustness, not for the temporal models:

  * UCI Taiwanese Bankruptcy Prediction (6,819 firms, 95 features, single
    snapshot)
  * UCI Polish Companies Bankruptcy (5 ARFF files, 1-5 years before the event)
  * Kaggle US Company Bankruptcy Prediction (needs an API token; instructions
    are written to the README and the step is skipped rather than blocking)

Load-and-describe only, per the spec. Note these hosts are *not* sec.gov, so
they are fetched with a neutral User-Agent - the SEC contact address is only
ever sent to the SEC.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import requests

import config as C

REPORT = C.REPORTS / "external_datasets_report.md"
GENERIC_UA = "Mozilla/5.0 (compatible; academic-research-dataset-builder/1.0)"

SOURCES = {
    "taiwanese": {
        "url": "https://archive.ics.uci.edu/static/public/572/taiwanese+bankruptcy+prediction.zip",
        "dir": C.EXTERNAL / "taiwanese",
        "label_col": "Bankrupt?",
    },
    "polish": {
        "url": "https://archive.ics.uci.edu/static/public/365/polish+companies+bankruptcy+data.zip",
        "dir": C.EXTERNAL / "polish",
        "label_col": "class",
    },
}

KAGGLE_INSTRUCTIONS = """\
### Kaggle - US Company Bankruptcy Prediction Dataset

Not downloaded automatically: Kaggle requires an authenticated API token, and
the pipeline takes no credentials. To add it:

1. Create a free account at https://www.kaggle.com and go to
   *Settings -> API -> Create New Token*. This downloads `kaggle.json`.
2. Place it at `%USERPROFILE%\\.kaggle\\kaggle.json` (Windows) or
   `~/.kaggle/kaggle.json` (Linux/macOS), then `chmod 600` it on POSIX.
3. Install and download:

```bash
pip install kaggle && kaggle datasets download -d utkarshx27/american-companies-bankruptcy-prediction-dataset -p data/external/kaggle_us --unzip
```

4. Re-run `python src/phase6_external.py`, which will pick up any CSV found
   under `data/external/kaggle_us/` and describe it alongside the others.
"""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": GENERIC_UA})
    return s


def fetch(name: str, force: bool = False) -> Path | None:
    spec = SOURCES[name]
    dest_dir: Path = spec["dir"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"{name}.zip"

    if not zip_path.exists() or force:
        try:
            print(f"[external] downloading {name} from UCI")
            r = _session().get(spec["url"], timeout=180)
            r.raise_for_status()
            zip_path.write_bytes(r.content)
        except Exception as exc:                       # noqa: BLE001
            print(f"[external] {name} download failed ({exc}) - skipping")
            return None
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile:
        print(f"[external] {name}: not a valid zip - skipping")
        return None
    print(f"[external] {name} ready in {dest_dir.relative_to(C.ROOT)}")
    return dest_dir


# ---------------------------------------------------------------------------
# Loaders (one per dataset, importable from analysis notebooks)
# ---------------------------------------------------------------------------
def load_taiwanese() -> pd.DataFrame | None:
    d = SOURCES["taiwanese"]["dir"]
    csvs = sorted(d.glob("*.csv"))
    if not csvs:
        return None
    return pd.read_csv(csvs[0])


def load_polish() -> dict[str, pd.DataFrame]:
    """Returns {'1year': df, ...}; ARFF parsed with scipy."""
    from scipy.io import arff

    out: dict[str, pd.DataFrame] = {}
    for f in sorted(SOURCES["polish"]["dir"].glob("*.arff")):
        try:
            data, _ = arff.loadarff(f)
        except Exception:                              # noqa: BLE001
            continue
        df = pd.DataFrame(data)
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = pd.to_numeric(df[c].astype(str).str.strip("b'\""),
                                      errors="coerce")
        out[f.stem] = df
    return out


def load_kaggle_us() -> pd.DataFrame | None:
    d = C.EXTERNAL / "kaggle_us"
    csvs = sorted(d.glob("*.csv")) if d.exists() else []
    if not csvs:
        return None
    return pd.read_csv(csvs[0])


# ---------------------------------------------------------------------------
def describe(name: str, df: pd.DataFrame, label_col: str | None) -> list[str]:
    L = [f"### {name}", "",
         f"- rows: **{len(df):,}**, columns: **{df.shape[1]}**"]
    if label_col and label_col in df.columns:
        vc = df[label_col].value_counts(dropna=False)
        pos = int(vc.get(1, vc.get(1.0, 0)))
        L += [f"- label column: `{label_col}`",
              f"- positives: **{pos:,}** ({100 * pos / len(df):.2f}%), "
              f"negatives: {len(df) - pos:,}"]
    num = df.select_dtypes("number")
    L += [f"- numeric columns: {num.shape[1]}",
          f"- cells missing: {100 * df.isna().mean().mean():.3f}%",
          f"- first columns: {', '.join(map(str, list(df.columns)[:6]))}", ""]
    return L


def main(force: bool = False) -> None:
    print("=" * 70)
    print("PHASE 6 - SUPPLEMENTARY DATASETS")
    print("=" * 70)
    L = ["# Phase 6 - Supplementary External Datasets", "",
         "Loaded and described only, per the spec; no processing beyond this.",
         "Each has a loader in `src/phase6_external.py`", "",
         "| Dataset | Loader |", "|---|---|",
         "| UCI Taiwanese | `load_taiwanese()` |",
         "| UCI Polish | `load_polish()` -> dict of 5 frames |",
         "| Kaggle US | `load_kaggle_us()` |", ""]

    for name in SOURCES:
        fetch(name, force=force)

    tw = load_taiwanese()
    if tw is not None:
        L += describe("UCI Taiwanese Bankruptcy Prediction", tw,
                      SOURCES["taiwanese"]["label_col"])
    else:
        L += ["### UCI Taiwanese Bankruptcy Prediction", "",
              "- not available (download failed or file absent)", ""]

    pol = load_polish()
    if pol:
        L += ["### UCI Polish Companies Bankruptcy", "",
              "Five files, one per years-before-bankruptcy horizon:", "",
              "| File | Rows | Cols | Positives | Positive rate | Missing cells |",
              "|---|---:|---:|---:|---:|---:|"]
        for k, df in sorted(pol.items()):
            lab = "class" if "class" in df.columns else df.columns[-1]
            pos = int((df[lab] == 1).sum())
            L.append(f"| `{k}` | {len(df):,} | {df.shape[1]} | {pos:,} | "
                     f"{100 * pos / len(df):.2f}% | "
                     f"{100 * df.isna().mean().mean():.2f}% |")
        L.append("")
    else:
        L += ["### UCI Polish Companies Bankruptcy", "",
              "- not available (download failed or ARFF files absent)", ""]

    kg = load_kaggle_us()
    if kg is not None:
        L += describe("Kaggle US Company Bankruptcy Prediction", kg,
                      "status_label" if "status_label" in kg.columns else None)
    else:
        L += [KAGGLE_INSTRUCTIONS, ""]

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {REPORT.relative_to(C.ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    main(**vars(ap.parse_args()))
