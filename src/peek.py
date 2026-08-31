"""Browse the dataset from the command line.

The headline outputs are Parquet and NPZ, which no text editor will open. This
prints them.

    python src/peek.py                      # what exists, and how big
    python src/peek.py labels               # bankrupt firms
    python src/peek.py panel                # raw XBRL inputs per firm-quarter
    python src/peek.py ratios               # the 29 features per firm-quarter
    python src/peek.py sequences            # the model-ready tensors
    python src/peek.py manifest             # one row per 8-quarter window
    python src/peek.py firm 320193          # everything about one company
    python src/peek.py firm "TOYS R US"     # ...by name too
    python src/peek.py export ratios out.csv    # dump any table to CSV/Excel

Add --rows N to show more rows, --split test to filter sequences.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import config as C

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 50)


TABLES = {
    "labels": (C.PROCESSED / "labels.csv", "one row per bankrupt firm"),
    "events": (C.PROCESSED / "labels_events.csv", "one row per bankruptcy event"),
    "universe": (C.DATA / "universe_pilot.csv", "the pilot firm list"),
    "panel": (C.INTERIM / "fundamentals_panel.parquet", "raw XBRL inputs per firm-quarter"),
    "ratios": (C.PROCESSED / "ratios_panel.parquet", "the 29 features per firm-quarter"),
    "manifest": (C.PROCESSED / "split_manifest.csv", "one row per 8-quarter window"),
    "unmatched": (C.REPORTS / "unmatched_positives.csv", "positives that could not enter the panel"),
}


def load(name: str) -> pd.DataFrame:
    path, _ = TABLES[name]
    if not path.exists():
        raise SystemExit(f"{path} not found - run `python run_all.py` first")
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"cik": str})


def _h(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
def cmd_overview() -> None:
    _h("FILES ON DISK")
    rows = []
    for name, (path, desc) in TABLES.items():
        rows.append({"name": name, "file": path.relative_to(C.ROOT).as_posix(),
                     "MB": round(path.stat().st_size / 1e6, 2) if path.exists() else 0,
                     "exists": path.exists(), "what": desc})
    for s in ("train", "val", "test"):
        p = C.PROCESSED / f"sequences_{s}.npz"
        rows.append({"name": f"sequences[{s}]", "file": p.relative_to(C.ROOT).as_posix(),
                     "MB": round(p.stat().st_size / 1e6, 2) if p.exists() else 0,
                     "exists": p.exists(), "what": "model-ready tensors"})
    print(pd.DataFrame(rows).to_string(index=False))

    _h("SHAPES")
    for name in TABLES:
        if TABLES[name][0].exists():
            df = load(name)
            print(f"  {name:<12} {len(df):>8,} rows x {df.shape[1]:>3} cols")
    for s in ("train", "val", "test"):
        p = C.PROCESSED / f"sequences_{s}.npz"
        if p.exists():
            with np.load(p) as z:
                print(f"  sequences[{s}]  X={z['X'].shape}  y={z['y'].shape}")

    print("\nRun `python src/peek.py <name>` to look inside any of these.")
    print("Reports in reports/ are plain markdown - open them in any editor.")


def cmd_table(name: str, rows: int) -> None:
    df = load(name)
    _h(f"{name.upper()}  -  {TABLES[name][1]}")
    print(f"{len(df):,} rows x {df.shape[1]} columns")
    print(f"\nColumns: {', '.join(df.columns[:40])}"
          + (" ..." if df.shape[1] > 40 else ""))

    if name == "labels":
        print(f"\nIn study window 2010-2024: {int(df['in_window'].sum()):,}")
        print("\nBy source:")
        print(df[df.in_window == 1]["source"].value_counts().to_string())
        print("\nBy year:")
        yr = pd.to_datetime(df[df.in_window == 1]["event_date"]).dt.year
        print(yr.value_counts().sort_index().to_string())
        show = df[df.in_window == 1][["cik", "company", "event_date", "chapter",
                                      "source", "n_events"]]
    elif name in ("panel", "ratios"):
        print(f"\nFirms: {df['cik'].nunique():,}   "
              f"Quarters: {df['quarter'].min()} to {df['quarter'].max()}")
        cols = ([c for c in ["cik", "company", "quarter", "Assets", "Revenue",
                             "NetIncomeLoss", "OCF", "TotalDebt"] if c in df]
                if name == "panel" else
                ["cik", "company", "quarter"] + C.RATIO_NAMES[:6])
        show = df[cols]
    elif name == "manifest":
        print("\nWindows per split:")
        print(df.groupby("split").agg(windows=("cik", "size"),
                                      firms=("cik", "nunique"),
                                      pos_y4=("y4", "sum")).to_string())
        show = df[["cik", "company", "start_quarter", "end_quarter", "split",
                   "y1", "y2", "y3", "y4", "n_observed_quarters"]]
    else:
        show = df

    print(f"\nFirst {rows} rows:")
    print(show.head(rows).to_string(index=False))


def cmd_sequences(split: str | None, rows: int) -> None:
    for s in (["train", "val", "test"] if split is None else [split]):
        p = C.PROCESSED / f"sequences_{s}.npz"
        if not p.exists():
            continue
        with np.load(p) as z:
            _h(f"SEQUENCES [{s}]  -  {p.relative_to(C.ROOT).as_posix()}")
            for k in z.files:
                a = z[k]
                print(f"  {k:<18} {str(a.shape):<20} {a.dtype}")
            y = z["y"]
            print(f"\n  windows: {len(y):,}   firms: {len(set(z['cik'].tolist())):,}")
            print("  positives per horizon: " +
                  ", ".join(f"y{h}={int(y[:, i].sum()):,} "
                            f"({100 * y[:, i].mean():.2f}%)"
                            for i, h in enumerate(z["horizons"])))
            print(f"  quarter range: {min(z['start_quarter'])} to {max(z['end_quarter'])}")

            print(f"\n  First {rows} windows (index arrays):")
            idx = pd.DataFrame({
                "cik": z["cik"][:rows], "start": z["start_quarter"][:rows],
                "end": z["end_quarter"][:rows],
                **{f"y{h}": y[:rows, i] for i, h in enumerate(z["horizons"])},
                "positive_firm": z["is_positive_firm"][:rows]})
            print(idx.to_string(index=False))

            # Show one positive window in full so the tensor is legible.
            pos = np.flatnonzero(y[:, -1] == 1)
            if len(pos):
                i = int(pos[0])
                print(f"\n  Example POSITIVE window - CIK {z['cik'][i]}, "
                      f"{z['start_quarter'][i]} to {z['end_quarter'][i]}, "
                      f"y={y[i].tolist()}")
                block = pd.DataFrame(z["X"][i], columns=z["feature_names"])
                block.index = [f"t-{7 - k}" for k in range(8)]
                print(block.iloc[:, :8].round(2).to_string())
                print("  (z-scored; first 8 of 29 features shown)")


def cmd_firm(query: str) -> None:
    ratios = load("ratios")
    panel = load("panel")
    labels = load("labels")

    q = str(query).strip()
    sel = ratios[ratios["cik"].astype(str) == q.lstrip("0")]
    if sel.empty:
        m = ratios["company"].astype(str).str.contains(q, case=False, na=False)
        sel = ratios[m]
    if sel.empty:
        raise SystemExit(f"no firm matching {query!r} in the ratio panel")

    cik = sel["cik"].iloc[0]
    name = sel["company"].iloc[0]
    _h(f"{name}  (CIK {cik})")

    lab = labels[labels["cik"].astype(str) == str(cik)]
    if len(lab):
        r = lab.iloc[0]
        print(f"  BANKRUPT: event {r['event_date']}  chapter {r['chapter']}  "
              f"source {r['source']}  events {r['n_events']} ({r['all_event_dates']})")
    else:
        print("  survivor (no bankruptcy event in 2010-2024)")

    pf = panel[panel["cik"].astype(str) == str(cik)]
    print(f"  {len(pf)} firm-quarters, {pf['quarter'].min()} to {pf['quarter'].max()}")

    print("\n  Raw XBRL inputs (last 8 quarters, $m):")
    cols = [c for c in ["quarter", "Assets", "AssetsCurrent", "LiabilitiesCurrent",
                        "Liabilities", "StockholdersEquity", "Revenue", "COGS",
                        "NetIncomeLoss", "EBIT", "OCF", "TotalDebt"] if c in pf]
    tail = pf[cols].tail(8).copy()
    for c in cols[1:]:
        tail[c] = (tail[c] / 1e6).round(1)
    print(tail.to_string(index=False))

    print("\n  Provenance - which XBRL tag supplied each value (most recent quarter):")
    last = pf.iloc[-1]
    for c in ["Assets", "Revenue", "NetIncomeLoss", "OCF", "TotalDebt", "InterestExpense"]:
        src = last.get(f"{c}__src")
        print(f"    {c:<18} {src if pd.notna(src) else '(not populated)'}")

    print("\n  Ratios (last 8 quarters, winsorised):")
    show = ["quarter", "r01_current_ratio", "r04_wc_to_ta", "r06_roa",
            "r10_re_to_ta", "r12_debt_to_assets", "r13_interest_coverage",
            "r25_ocf_to_cl", "r29_negative_equity_flag"]
    print(sel[show].tail(8).round(3).to_string(index=False))

    man_path = C.PROCESSED / "split_manifest.csv"
    if man_path.exists():
        man = pd.read_csv(man_path, dtype={"cik": str})
        mf = man[man["cik"].astype(str) == str(cik)]
        print(f"\n  {len(mf)} sequence windows built for this firm:")
        if len(mf):
            print(mf[["start_quarter", "end_quarter", "split",
                      "y1", "y2", "y3", "y4"]].tail(8).to_string(index=False))


def cmd_export(name: str, out: str) -> None:
    df = load(name)
    p = Path(out)
    if p.suffix.lower() in (".xlsx", ".xls"):
        df.to_excel(p, index=False)
    else:
        df.to_csv(p, index=False)
    print(f"wrote {len(df):,} rows x {df.shape[1]} cols -> {p}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?", default="overview",
                    help="overview | " + " | ".join(TABLES) + " | sequences | firm | export")
    ap.add_argument("arg", nargs="?", help="firm id/name, or export target file")
    ap.add_argument("arg2", nargs="?", help="export output path")
    ap.add_argument("--rows", type=int, default=10)
    ap.add_argument("--split", choices=["train", "val", "test"])
    a = ap.parse_args()

    if a.what == "overview":
        cmd_overview()
    elif a.what in TABLES:
        cmd_table(a.what, a.rows)
    elif a.what == "sequences":
        cmd_sequences(a.split, a.rows)
    elif a.what == "firm":
        if not a.arg:
            raise SystemExit("usage: python src/peek.py firm <cik|name>")
        cmd_firm(a.arg)
    elif a.what == "export":
        if not a.arg or not a.arg2:
            raise SystemExit("usage: python src/peek.py export <table> <out.csv>")
        cmd_export(a.arg, a.arg2)
    else:
        raise SystemExit(f"unknown: {a.what}")


if __name__ == "__main__":
    main()
