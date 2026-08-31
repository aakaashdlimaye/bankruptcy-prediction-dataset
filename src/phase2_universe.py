"""Phase 2 - Firm universe and pilot sample.

Universe rule: a CIK is in scope if it filed at least one 10-K or 10-Q with a
period end inside 2010-2024 and its SIC is outside 6000-6799 (financials,
insurance, real estate).

SIC resolution chain: submissions.zip (SEC's current assignment) -> the SIC
carried on the firm's own EDGAR full-text-search hits -> LoPucki SICPrimary.
Firms that resolve to no SIC at all are kept but flagged, because dropping them
would silently discard bankrupt micro-caps.

Pilot universe (spec): every bankrupt firm we can identify, plus a seeded
random sample of survivors. Positives are never subsampled.

Outputs
-------
data/interim/universe_full.parquet   every in-scope firm with its flags
data/universe_pilot.csv              the pilot firm list
reports/unmatched_positives.csv      positives that cannot enter the panel
reports/universe_report.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import config as C

META = C.INTERIM / "company_meta.parquet"
LABELS = C.PROCESSED / "labels.csv"
CF_ZIP = C.RAW / "companyfacts.zip"
CF_INDEX = C.INTERIM / "companyfacts_ciks.txt"

UNIVERSE_FULL = C.INTERIM / "universe_full.parquet"
UNIVERSE_PILOT = C.DATA / "universe_pilot.csv"
UNMATCHED_POS = C.REPORTS / "unmatched_positives.csv"
REPORT = C.REPORTS / "universe_report.md"

CF_NAME_RE = re.compile(r"CIK(\d{10})\.json$")


def companyfacts_ciks(force: bool = False) -> set[str]:
    """CIKs that have an entry in companyfacts.zip (reads the zip index only)."""
    if CF_INDEX.exists() and not force:
        return set(CF_INDEX.read_text().split())
    if not CF_ZIP.exists():
        raise SystemExit(f"missing {CF_ZIP}; run src/download_bulk.py first")
    with zipfile.ZipFile(CF_ZIP) as zf:
        ciks = {str(int(m.group(1)))
                for n in zf.namelist() if (m := CF_NAME_RE.search(n))}
    CF_INDEX.write_text("\n".join(sorted(ciks, key=int)))
    print(f"[universe] companyfacts.zip holds {len(ciks):,} CIKs")
    return ciks


def load_tickers() -> pd.DataFrame:
    path = C.RAW / "company_tickers.json"
    if not path.exists():
        return pd.DataFrame(columns=["cik", "ticker", "title"])
    blob = json.loads(path.read_text(encoding="utf-8"))
    rows = blob.values() if isinstance(blob, dict) else blob
    df = pd.DataFrame(rows)
    df["cik"] = df["cik_str"].astype(int).astype(str)
    return (df[["cik", "ticker", "title"]]
            .drop_duplicates("cik", keep="first"))


def _resolve_sic(meta: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """submissions SIC -> EFTS hit SIC -> LoPucki SIC."""
    meta = meta.copy()
    meta["sic_source"] = np.where(meta["sic"].notna(), "submissions", "")

    extra: dict[str, tuple[str, float]] = {}
    efts_path = C.INTERIM / "efts_8k_item103.csv"
    if efts_path.exists():
        e = pd.read_csv(efts_path, dtype={"cik": str})
        for cik, sic in zip(e["cik"].astype(str), e["sic"]):
            if pd.notna(sic) and cik:
                extra.setdefault(cik, ("efts", float(sic)))
    for cik, sic in zip(labels["cik"].astype(str), labels["sic"]):
        if pd.notna(sic) and cik:
            try:
                extra.setdefault(cik, ("lopucki", float(sic)))
            except (TypeError, ValueError):
                pass

    need = meta["sic"].isna().to_numpy()
    if need.any() and extra:
        ciks = meta["cik"].to_numpy()
        sic_col = meta["sic"].to_numpy(dtype=float, copy=True)
        src_col = meta["sic_source"].to_numpy(dtype=object, copy=True)
        for i in np.flatnonzero(need):
            hit = extra.get(ciks[i])
            if hit is not None:
                src_col[i], sic_col[i] = hit[0], hit[1]
        meta["sic"] = sic_col
        meta["sic_source"] = src_col
    return meta


def build_universe(force: bool = False) -> pd.DataFrame:
    if UNIVERSE_FULL.exists() and not force:
        print(f"[universe] cached -> {UNIVERSE_FULL.name}")
        return pd.read_parquet(UNIVERSE_FULL)

    meta = pd.read_parquet(META)
    meta["cik"] = meta["cik"].astype(str)
    labels = pd.read_csv(LABELS, dtype={"cik": str})
    labels["event_date"] = pd.to_datetime(labels["event_date"])

    meta = _resolve_sic(meta, labels)
    cf = companyfacts_ciks(force=force)
    tick = load_tickers()

    meta = meta.merge(tick, on="cik", how="left")
    meta["has_companyfacts"] = meta["cik"].isin(cf).astype(int)
    meta["sic_known"] = meta["sic"].notna().astype(int)
    meta["is_financial"] = (meta["sic"].notna() &
                            meta["sic"].between(C.SIC_EXCLUDE_LO,
                                                C.SIC_EXCLUDE_HI)).astype(int)

    lab = labels.set_index("cik")
    meta["is_bankrupt"] = meta["cik"].isin(lab.index).astype(int)
    meta["event_date"] = meta["cik"].map(lab["event_date"])
    meta["event_in_window"] = meta["cik"].map(lab["in_window"]).fillna(0).astype(int)

    meta["in_universe"] = ((meta["has_periodic_in_window"] == 1) &
                           (meta["is_financial"] == 0) &
                           (meta["has_companyfacts"] == 1)).astype(int)

    meta.to_parquet(UNIVERSE_FULL, index=False)
    print(f"[universe] {int(meta['in_universe'].sum()):,} firms in scope "
          f"-> {UNIVERSE_FULL.name}")
    return meta


def audit_positives(uni: pd.DataFrame) -> pd.DataFrame:
    """Every labelled bankrupt firm either enters the panel or is logged here."""
    labels = pd.read_csv(LABELS, dtype={"cik": str})
    labels = labels[labels["in_window"] == 1].copy()
    u = uni.set_index("cik")

    rows = []
    for _, r in labels.iterrows():
        cik = r["cik"]
        if cik not in u.index:
            rows.append({**r, "reason": "CIK absent from submissions.zip "
                                        "(no EDGAR filing history at all)"})
            continue
        m = u.loc[cik]
        if m["has_periodic_in_window"] != 1:
            rows.append({**r, "reason": "no 10-K/10-Q with a period end in 2010-2024"})
        elif m["is_financial"] == 1:
            rows.append({**r, "reason": "SIC excluded (financial 6000-6799)",
                         "excluded_sic": int(m["sic"])})
        elif m["has_companyfacts"] != 1:
            rows.append({**r, "reason": "no entry in companyfacts.zip (never filed XBRL)"})
    out = pd.DataFrame(rows)
    if not out.empty:
        if "excluded_sic" not in out.columns:
            out["excluded_sic"] = pd.NA
        out = out[["cik", "company", "event_date", "source", "chapter", "sic",
                   "excluded_sic", "reason"]]
    out.to_csv(UNMATCHED_POS, index=False)
    print(f"[universe] {len(out):,} positives cannot enter the panel "
          f"-> {UNMATCHED_POS.name}")
    return out


def build_pilot(uni: pd.DataFrame, target: int = C.PILOT_TARGET_FIRMS,
                seed: int = C.RANDOM_SEED) -> pd.DataFrame:
    scope = uni[uni["in_universe"] == 1].copy()
    pos = scope[(scope["is_bankrupt"] == 1) & (scope["event_in_window"] == 1)]
    surv = scope[scope["is_bankrupt"] == 0]

    # Positives are never subsampled. Survivors fill up to the target, with a
    # floor so the negative class stays large enough to be informative even
    # when positives alone already exceed the target.
    n_surv = max(target - len(pos), len(pos))
    n_surv = min(n_surv, len(surv))
    samp = surv.sample(n=n_surv, random_state=seed)

    pilot = pd.concat([pos, samp], ignore_index=True)
    pilot["pilot_class"] = np.where(pilot["is_bankrupt"] == 1, "positive", "survivor")
    cols = ["cik", "name", "ticker", "sic", "sic_desc", "sic_source",
            "exchanges", "is_bankrupt", "event_date", "pilot_class",
            "n_10k_win", "n_10q_win", "first_period", "last_period",
            "last_filing", "has_companyfacts"]
    pilot = pilot[[c for c in cols if c in pilot.columns]].sort_values(
        ["pilot_class", "cik"]).reset_index(drop=True)
    pilot.to_csv(UNIVERSE_PILOT, index=False)
    print(f"[universe] pilot = {len(pos):,} positives + {len(samp):,} survivors "
          f"= {len(pilot):,} firms -> {UNIVERSE_PILOT.relative_to(C.ROOT)}")
    return pilot


def write_report(uni: pd.DataFrame, pilot: pd.DataFrame,
                 unmatched: pd.DataFrame) -> None:
    scope = uni[uni["in_universe"] == 1]
    lab_win = int(((uni["is_bankrupt"] == 1) & (uni["event_in_window"] == 1)).sum())
    pos_scope = int(((scope["is_bankrupt"] == 1) &
                     (scope["event_in_window"] == 1)).sum())
    reasons = (unmatched["reason"].value_counts() if not unmatched.empty
               else pd.Series(dtype=int))

    L = [
        "# Phase 2 - Firm Universe Report", "",
        "## Funnel", "",
        "| Step | Firms |", "|---|---:|",
        f"| CIKs in submissions.zip | {len(uni):,} |",
        f"| ... with a 10-K/10-Q period end in 2010-2024 | {int((uni['has_periodic_in_window'] == 1).sum()):,} |",
        f"| ... excluding SIC {C.SIC_EXCLUDE_LO}-{C.SIC_EXCLUDE_HI} (financials) | "
        f"{int(((uni['has_periodic_in_window'] == 1) & (uni['is_financial'] == 0)).sum()):,} |",
        f"| ... with an entry in companyfacts.zip | {int(scope.shape[0]):,} |",
        "", "## SIC resolution", "",
        "| Source of SIC | Firms in scope |", "|---|---:|",
    ] + [f"| {k or 'unresolved (kept, flagged)'} | {v:,} |"
         for k, v in scope["sic_source"].fillna("").value_counts().items()] + [
        "", "## Positive class", "",
        f"- Labelled bankrupt firms with event in 2010-2024: **{lab_win:,}**",
        f"- ... that survive the universe filters and can enter the panel: **{pos_scope:,}**",
        f"- ... logged in `reports/unmatched_positives.csv` instead: **{len(unmatched):,}**",
        "", "| Reason a positive cannot enter the panel | Firms |", "|---|---:|",
    ] + [f"| {k} | {v:,} |" for k, v in reasons.items()] + [
        "", "## Pilot universe", "",
        f"- Positives (all of them - never subsampled): "
        f"**{int((pilot['pilot_class'] == 'positive').sum()):,}**",
        f"- Survivors (random, seed={C.RANDOM_SEED}): "
        f"**{int((pilot['pilot_class'] == 'survivor').sum()):,}**",
        f"- Total pilot firms: **{len(pilot):,}**",
        "",
        "The pilot is deliberately positive-enriched: the spec forbids subsampling",
        "the positive class, and the identified positives alone already exceed the",
        "~500-firm pilot budget. Class rates quoted for the pilot are therefore not",
        "population rates; the `--full` run restores the true base rate.", "",
    ]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {REPORT.relative_to(C.ROOT)}")


def main(force: bool = False, target: int = C.PILOT_TARGET_FIRMS) -> pd.DataFrame:
    print("=" * 70)
    print("PHASE 2 - FIRM UNIVERSE")
    print("=" * 70)
    uni = build_universe(force=force)
    unmatched = audit_positives(uni)
    pilot = build_pilot(uni, target=target)
    write_report(uni, pilot, unmatched)
    return pilot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--target", type=int, default=C.PILOT_TARGET_FIRMS)
    main(**vars(ap.parse_args()))
