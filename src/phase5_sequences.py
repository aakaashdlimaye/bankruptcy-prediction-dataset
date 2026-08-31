"""Phase 5 - Firm-quarter labelling, sequence construction and the split.

Key rules, all of which are audited in reports/leakage_audit.md:

* **The dropout trap.** Bankrupt firms stop filing before they file for
  bankruptcy, so the look-back window ends at the firm's *last available
  filing*, never at the bankruptcy date. A window whose most recent quarter is
  three quarters before the event is still a valid positive - it simply has
  y_1 = y_2 = 0 and y_3 = y_4 = 1.
* **Post-petition data is excluded.** Any firm-quarter whose period end is on
  or after the event date is dropped entirely.
* **Horizon labels.** y_h = 1 when the event falls within h quarters after the
  end of quarter t, measured in real time from the period end.
* **Forward fill is bounded** at 2 quarters and can never cross an event date,
  because post-event rows are already gone before filling happens.
* **Winsorisation and the scaler are fitted on the training period only.**

Outputs: data/processed/sequences_{train,val,test}.npz,
         data/processed/split_manifest.csv, data/processed/scaler_params.json,
         reports/leakage_audit.md, reports/sequences_report.md
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
import xbrl_extract as X

LABELS = C.PROCESSED / "labels.csv"
MANIFEST = C.PROCESSED / "split_manifest.csv"
SCALER = C.PROCESSED / "scaler_params.json"
AUDIT = C.REPORTS / "leakage_audit.md"
SEQ_REPORT = C.REPORTS / "sequences_report.md"

FEATURES = C.RATIO_NAMES
NF = len(FEATURES)
DAYS_PER_Q = 365.25 / 4.0

TRAIN_END_IDX = X.quarter_to_index(C.TRAIN_END)
VAL_START_IDX = X.quarter_to_index(C.VAL_START)
VAL_END_IDX = X.quarter_to_index(C.VAL_END)
TEST_START_IDX = X.quarter_to_index(C.TEST_START)
TEST_END_IDX = X.quarter_to_index(C.TEST_END)


def split_of(end_idx: int) -> str | None:
    if end_idx <= TRAIN_END_IDX:
        return "train"
    if VAL_START_IDX <= end_idx <= VAL_END_IDX:
        return "val"
    if TEST_START_IDX <= end_idx <= TEST_END_IDX:
        return "test"
    return None


# ---------------------------------------------------------------------------
# Step 1-2: label firm-quarters
# ---------------------------------------------------------------------------
def label_firm_quarters(p: pd.DataFrame, labels: pd.DataFrame
                        ) -> tuple[pd.DataFrame, pd.DataFrame]:
    lab = labels[labels["in_window"] == 1].set_index("cik")
    p = p.copy()
    p["period_end"] = pd.to_datetime(p["period_end"])
    p["event_date"] = pd.to_datetime(p["cik"].map(lab["event_date"]))
    p["is_positive_firm"] = p["event_date"].notna().astype(int)

    n_before = len(p)
    post = p["event_date"].notna() & (p["period_end"] >= p["event_date"])
    dropout = _dropout_table(p, post)
    p = p[~post].copy()
    print(f"[label] dropped {int(post.sum()):,} post-petition firm-quarters "
          f"of {n_before:,}")

    gap_days = (p["event_date"] - p["period_end"]).dt.days
    qa = np.ceil(gap_days / DAYS_PER_Q)
    p["quarters_to_event"] = np.where(p["event_date"].notna(),
                                      np.maximum(qa.fillna(0), 1), np.nan)
    for h in C.HORIZONS:
        p[f"y{h}"] = ((p["quarters_to_event"].notna()) &
                      (p["quarters_to_event"] <= h)).astype(np.int8)
    return p, dropout


def _dropout_table(p: pd.DataFrame, post: pd.Series) -> pd.DataFrame:
    """Distribution of (event date - last available filing) in quarters."""
    pre = p[~post & p["event_date"].notna()]
    if pre.empty:
        return pd.DataFrame()
    last = pre.groupby("cik").agg(last_period=("period_end", "max"),
                                  event_date=("event_date", "first"))
    last["gap_days"] = (last["event_date"] - last["last_period"]).dt.days
    last["gap_quarters"] = np.ceil(last["gap_days"] / DAYS_PER_Q).astype(int)
    return last.reset_index()


# ---------------------------------------------------------------------------
# Step 3: forward fill and windowing
# ---------------------------------------------------------------------------
def prepare_firm(g: pd.DataFrame) -> pd.DataFrame:
    """Reindex one firm onto a contiguous quarter grid and forward-fill <= 2."""
    g = g.sort_values("quarter_idx")
    lo, hi = int(g["quarter_idx"].min()), int(g["quarter_idx"].max())
    grid = pd.RangeIndex(lo, hi + 1)
    g = g.set_index("quarter_idx").reindex(grid)
    g["was_observed"] = g["period_end"].notna().astype(int)
    g[FEATURES] = g[FEATURES].ffill(limit=C.MAX_FFILL_GAP)
    for c in ["cik", "company", "is_bankrupt", "event_date", "is_positive_firm",
              "has_inventory", "has_debt"]:
        if c in g:
            g[c] = g[c].ffill().bfill()
    for c in ["quarters_to_event"] + [f"y{h}" for h in C.HORIZONS]:
        if c in g:
            g[c] = g[c].ffill(limit=C.MAX_FFILL_GAP)
    g.index.name = "quarter_idx"
    return g.reset_index()


def build_windows(p: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                            np.ndarray, pd.DataFrame]:
    L, S = C.WINDOW_LEN, C.WINDOW_STRIDE
    Xs, Ms, Ys, Is, rows = [], [], [], [], []
    n_reject_complete = n_reject_endghost = 0

    for cik, g in p.groupby("cik", sort=False):
        g = prepare_firm(g)
        feat = g[FEATURES].to_numpy(dtype=np.float64)
        obs = g["was_observed"].to_numpy()
        ind = g[["has_inventory", "has_debt"]].to_numpy(dtype=np.float64)
        qidx = g["quarter_idx"].to_numpy()
        n = len(g)
        for s in range(0, n - L + 1, S):
            e = s + L - 1
            end_idx = int(qidx[e])
            if split_of(end_idx) is None:
                continue
            # The labelled quarter must be a real filing, not a filled phantom.
            if obs[e] != 1:
                n_reject_endghost += 1
                continue
            blk = feat[s:e + 1]
            nonnull_per_feature = np.isfinite(blk).sum(axis=0)
            if nonnull_per_feature.mean() < C.MIN_NONNULL_QUARTERS:
                n_reject_complete += 1
                continue
            row = g.iloc[e]
            Xs.append(blk)
            Ms.append(np.isfinite(blk).astype(np.uint8))
            Ys.append([int(row.get(f"y{h}", 0) or 0) for h in C.HORIZONS])
            Is.append(ind[s:e + 1])
            rows.append({
                "cik": cik,
                "company": row.get("company"),
                "start_quarter": X.index_to_quarter(int(qidx[s])),
                "end_quarter": X.index_to_quarter(end_idx),
                "end_quarter_idx": end_idx,
                "start_quarter_idx": int(qidx[s]),
                "split": split_of(end_idx),
                "is_positive_firm": int(row.get("is_positive_firm", 0) or 0),
                "event_date": row.get("event_date"),
                "quarters_to_event": row.get("quarters_to_event"),
                "n_observed_quarters": int(obs[s:e + 1].sum()),
                "pct_cells_present": float(100 * np.isfinite(blk).mean()),
                **{f"y{h}": int(row.get(f"y{h}", 0) or 0) for h in C.HORIZONS},
            })
    print(f"[window] rejected {n_reject_complete:,} windows on completeness, "
          f"{n_reject_endghost:,} whose end quarter was forward-filled")
    man = pd.DataFrame(rows)
    return (np.asarray(Xs, dtype=np.float64), np.asarray(Ms, dtype=np.uint8),
            np.asarray(Ys, dtype=np.int8), np.asarray(Is, dtype=np.float32), man)


# ---------------------------------------------------------------------------
# Step 5: scaler fitted on train only
# ---------------------------------------------------------------------------
def fit_scaler(Xtr: np.ndarray) -> dict:
    flat = Xtr.reshape(-1, NF)
    mean = np.nanmean(np.where(np.isfinite(flat), flat, np.nan), axis=0)
    std = np.nanstd(np.where(np.isfinite(flat), flat, np.nan), axis=0)
    std = np.where((std == 0) | ~np.isfinite(std), 1.0, std)
    mean = np.where(np.isfinite(mean), mean, 0.0)
    return {"feature_names": FEATURES, "mean": mean.tolist(), "std": std.tolist(),
            "fitted_on": "train split only (window end quarter <= "
                         f"{C.TRAIN_END})",
            "n_train_windows": int(Xtr.shape[0]),
            "imputation": "cells still missing after forward fill are set to the "
                          "train mean, i.e. 0 after standardisation; the mask "
                          "array marks them"}


def apply_scaler(Xa: np.ndarray, sc: dict) -> np.ndarray:
    mean = np.asarray(sc["mean"], dtype=np.float64)
    std = np.asarray(sc["std"], dtype=np.float64)
    Z = (Xa - mean) / std
    return np.where(np.isfinite(Z), Z, 0.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main(embargo: bool = False, full: bool = False) -> dict:
    RATIOS = C.ratios_path(full)
    print("=" * 70)
    print("PHASE 5 - LABELLING AND SEQUENCE CONSTRUCTION")
    print("=" * 70)
    p = pd.read_parquet(RATIOS)
    labels = pd.read_csv(LABELS, dtype={"cik": str})
    p, dropout = label_firm_quarters(p, labels)

    Xa, Ma, Ya, Ia, man = build_windows(p)
    print(f"[window] {len(man):,} windows built")
    if man.empty:
        raise SystemExit("no windows produced")

    if embargo:
        n0 = len(man)
        bad = ((man["split"] == "val") & (man["start_quarter_idx"] <= TRAIN_END_IDX)) | \
              ((man["split"] == "test") & (man["start_quarter_idx"] < TEST_START_IDX))
        keep = (~bad).to_numpy()
        Xa, Ma, Ya, Ia = Xa[keep], Ma[keep], Ya[keep], Ia[keep]
        man = man[keep].reset_index(drop=True)
        print(f"[window] embargo dropped {n0 - len(man):,} boundary-straddling windows")

    tr = (man["split"] == "train").to_numpy()
    sc = fit_scaler(Xa[tr])
    SCALER.write_text(json.dumps(sc, indent=2))
    print(f"[scale] fitted on {int(tr.sum()):,} train windows -> {SCALER.name}")

    Z = apply_scaler(Xa, sc)
    out_paths = {}
    for name in ("train", "val", "test"):
        m = (man["split"] == name).to_numpy()
        path = C.PROCESSED / f"sequences_{name}.npz"
        np.savez_compressed(
            path,
            X=Z[m], y=Ya[m], mask=Ma[m], indicators=Ia[m],
            X_unscaled=Xa[m].astype(np.float32),
            cik=man.loc[m, "cik"].to_numpy().astype("U12"),
            end_quarter=man.loc[m, "end_quarter"].to_numpy().astype("U6"),
            start_quarter=man.loc[m, "start_quarter"].to_numpy().astype("U6"),
            is_positive_firm=man.loc[m, "is_positive_firm"].to_numpy().astype(np.int8),
            feature_names=np.array(FEATURES, dtype="U40"),
            indicator_names=np.array(C.INDICATOR_NAMES, dtype="U20"),
            horizons=np.array(C.HORIZONS, dtype=np.int8))
        out_paths[name] = path
        print(f"[save] {name}: X{Z[m].shape} y{Ya[m].shape} -> {path.name}")

    man.to_csv(MANIFEST, index=False)
    print(f"[save] manifest -> {MANIFEST.relative_to(C.ROOT)}")

    write_sequences_report(man, dropout, p)
    ok = leakage_audit(man, p, sc, Xa, Ya)
    return {"manifest": man, "audit_pass": ok}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def write_sequences_report(man: pd.DataFrame, dropout: pd.DataFrame,
                           p: pd.DataFrame) -> None:
    L = ["# Phase 5 - Sequences Report", "",
         "## The dropout trap", "",
         "Bankrupt firms stop filing before the petition date, so the look-back",
         "window ends at the last available filing. Distribution of",
         "(event date - last available filing) for positives that reach the panel:",
         ""]
    if not dropout.empty:
        vc = dropout["gap_quarters"].clip(upper=9).value_counts().sort_index()
        L += ["| Quarters between last filing and event | Firms |", "|---:|---:|"]
        L += [f"| {int(k)}{'+' if k == 9 else ''} | {int(v):,} |" for k, v in vc.items()]
        L += ["",
              f"Median gap: **{dropout['gap_quarters'].median():.1f} quarters** "
              f"({dropout['gap_days'].median():.0f} days); mean "
              f"{dropout['gap_quarters'].mean():.2f}. "
              f"{int((dropout['gap_quarters'] >= 2).sum()):,} of "
              f"{len(dropout):,} positives ({100 * (dropout['gap_quarters'] >= 2).mean():.0f}%) "
              "stop filing at least two quarters ahead - anchoring windows to the",
              "bankruptcy date instead of the last filing would have discarded them.", ""]

    L += ["## Completeness rule", "",
          f"A window of {C.WINDOW_LEN} quarters is kept when, **averaged over the "
          f"{NF} features**, at least {C.MIN_NONNULL_QUARTERS} of the "
          f"{C.WINDOW_LEN} quarters are non-null:", "",
          "```",
          "mean_over_features( count_of_non_null_quarters(feature) ) >= 6",
          "```", "",
          "Two further conditions:", "",
          f"- gaps are forward-filled within a firm for at most "
          f"{C.MAX_FFILL_GAP} quarters before windowing, and never across an event "
          "date (post-petition rows are removed first, so no fill can cross one);",
          "- the window's **end quarter must be a real filing**, never a",
          "  forward-filled placeholder, because that quarter carries the label.", "",
          "## Window counts", "",
          "| Split | Window end quarters | Windows | Firms | Positive windows (y4) | Positive rate |",
          "|---|---|---:|---:|---:|---:|"]
    rng = {"train": f"<= {C.TRAIN_END}", "val": f"{C.VAL_START}-{C.VAL_END}",
           "test": f"{C.TEST_START}-{C.TEST_END}"}
    for s in ("train", "val", "test"):
        d = man[man["split"] == s]
        pos = int(d["y4"].sum())
        L.append(f"| {s} | {rng[s]} | {len(d):,} | {d['cik'].nunique():,} | {pos:,} | "
                 f"{100 * pos / max(len(d), 1):.2f}% |")
    L.append(f"| **all** | | **{len(man):,}** | **{man['cik'].nunique():,}** | "
             f"**{int(man['y4'].sum()):,}** | "
             f"**{100 * man['y4'].sum() / max(len(man), 1):.2f}%** |")

    L += ["", "## Positives per split and horizon", "",
          "| Split | " + " | ".join(f"y{h}" for h in C.HORIZONS) + " | windows |",
          "|---|" + "---:|" * (len(C.HORIZONS) + 1)]
    for s in ("train", "val", "test"):
        d = man[man["split"] == s]
        L.append(f"| {s} | " + " | ".join(f"{int(d[f'y{h}'].sum()):,}" for h in C.HORIZONS)
                 + f" | {len(d):,} |")

    L += ["", "## Data completeness of the retained windows", "",
          f"- mean share of observed (non-forward-filled) quarters per window: "
          f"**{man['n_observed_quarters'].mean():.2f} of {C.WINDOW_LEN}**",
          f"- mean share of non-null feature cells per window: "
          f"**{man['pct_cells_present'].mean():.1f}%**", ""]
    SEQ_REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {SEQ_REPORT.relative_to(C.ROOT)}")


def leakage_audit(man: pd.DataFrame, p: pd.DataFrame, sc: dict,
                  Xa: np.ndarray, Ya: np.ndarray) -> bool:
    win = json.loads((C.PROCESSED / "winsor_bounds.json").read_text())
    L = ["# Phase 5 Gate - Leakage Audit", "",
         "Each check prints the evidence it is asserting on.", ""]
    results = []

    # (a) no window index in two splits
    key = man["cik"].astype(str) + "|" + man["end_quarter"].astype(str)
    dup = man.assign(key=key).groupby("key")["split"].nunique()
    n_multi = int((dup > 1).sum())
    ok_a = n_multi == 0
    results.append(ok_a)
    counts = man.groupby("split").size().to_dict()
    L += ["## (a) No firm-quarter index appears in two splits", "",
          "```",
          f"window index = (cik, end_quarter); total windows = {len(man):,}",
          f"distinct window indices                = {dup.shape[0]:,}",
          f"indices mapped to more than one split  = {n_multi}",
          f"split sizes: {counts}",
          "```", "",
          f"**{'PASS' if ok_a else 'FAIL'}** - every window index belongs to exactly "
          "one split, because the split is a function of the end quarter alone.", ""]

    over = _boundary_overlap(man)
    L += ["> **Disclosed property of stride-1 windowing.** The spec assigns a "
          "straddling window to the split of its end quarter rather than dropping "
          "it, so *input quarters* near a boundary can appear in windows on both "
          "sides. Windows affected: "
          f"val {over['val']:,} of {counts.get('val', 0):,}, "
          f"test {over['test']:,} of {counts.get('test', 0):,}. "
          "No label is shared. Run with `--embargo` to drop these windows entirely.",
          ""]

    # (b) winsorisation and scaler fitted on train only
    ok_b = (win["fitted_on"].endswith(C.TRAIN_CUTOFF_DATE)
            and "train split only" in sc["fitted_on"])
    results.append(ok_b)
    tr_end = man.loc[man["split"] == "train", "end_quarter_idx"]
    L += ["## (b) Winsorisation and scaler parameters derive only from train data",
          "", "```",
          f"winsorisation fitted_on : {win['fitted_on']}",
          f"  rows used             : {win['n_train_rows']:,} of {win['n_total_rows']:,}",
          f"  example bound         : r13_interest_coverage p01="
          f"{win['bounds']['r13_interest_coverage']['p01']:.3f} "
          f"p99={win['bounds']['r13_interest_coverage']['p99']:.3f}",
          f"scaler fitted_on        : {sc['fitted_on']}",
          f"  windows used          : {sc['n_train_windows']:,}",
          f"  max train end quarter : {X.index_to_quarter(int(tr_end.max()))} "
          f"(limit {C.TRAIN_END})",
          "```", "",
          f"**{'PASS' if ok_b else 'FAIL'}** - both parameter sets are fitted on "
          f"period ends up to {C.TRAIN_CUTOFF_DATE} and applied unchanged to val "
          "and test.", ""]

    # (c) no window contains quarters at or after its firm's event date
    pos = man[man["is_positive_firm"] == 1].copy()
    pos["event_q"] = pos["event_date"].map(
        lambda d: X.quarter_to_index(X.quarter_label(pd.Timestamp(d).date()))
        if pd.notna(d) else np.nan)
    viol = pos[pos["end_quarter_idx"] > pos["event_q"]]
    post_rows = int((p["event_date"].notna() &
                     (p["period_end"] >= p["event_date"])).sum())
    ok_c = len(viol) == 0 and post_rows == 0
    results.append(ok_c)
    L += ["## (c) No window contains quarters at or after its firm's event date",
          "", "```",
          f"positive-firm windows checked            = {len(pos):,}",
          f"windows whose end quarter is past the    = {len(viol)}",
          "  firm's bankruptcy quarter",
          f"post-petition firm-quarters left in panel= {post_rows}",
          f"min quarters_to_event over positives     = "
          f"{pos['quarters_to_event'].min() if len(pos) else 'n/a'}",
          "```", "",
          f"**{'PASS' if ok_c else 'FAIL'}** - firm-quarters with a period end on or "
          "after the event date are removed before windowing, so no window can "
          "contain post-petition data.", ""]

    # (d) max quarter in train < min label horizon quarter in val
    max_tr = int(man.loc[man["split"] == "train", "end_quarter_idx"].max())
    val = man[man["split"] == "val"]
    min_val_h = int(val["end_quarter_idx"].min()) + 1 if len(val) else None
    ok_d = min_val_h is not None and max_tr < min_val_h
    results.append(ok_d)
    L += ["## (d) Max quarter in train < min label-horizon quarter in val", "",
          "```",
          f"max window end quarter in train      = {X.index_to_quarter(max_tr)}",
          f"min window end quarter in val        = "
          f"{X.index_to_quarter(int(val['end_quarter_idx'].min()))}",
          f"min label-horizon quarter in val (h=1) = {X.index_to_quarter(min_val_h)}",
          f"comparison: {X.index_to_quarter(max_tr)} < {X.index_to_quarter(min_val_h)} "
          f"-> {max_tr < min_val_h}",
          "```", "",
          f"**{'PASS' if ok_d else 'FAIL'}**", "",
          "> **Disclosed property.** A train window ending "
          f"{C.TRAIN_END} carries a y_4 label that resolves in "
          f"{X.index_to_quarter(TRAIN_END_IDX + 4)}, inside the validation period. "
          "This is inherent to multi-horizon labelling with an adjacent split and "
          "is reported rather than hidden; `--embargo` removes the affected "
          "boundary windows if a stricter protocol is wanted.", ""]

    all_ok = all(results)
    L += ["## Verdict", "",
          "| Check | Result |", "|---|---|",
          f"| (a) no firm-quarter index in two splits | {'PASS' if ok_a else 'FAIL'} |",
          f"| (b) winsoriser and scaler from train only | {'PASS' if ok_b else 'FAIL'} |",
          f"| (c) no window contains post-event quarters | {'PASS' if ok_c else 'FAIL'} |",
          f"| (d) train max quarter < val min label horizon | {'PASS' if ok_d else 'FAIL'} |",
          "", f"**Leakage audit: {'PASS' if all_ok else 'FAIL'}**", ""]
    AUDIT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {AUDIT.relative_to(C.ROOT)}")
    print(f"GATE: leakage audit -> {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def _boundary_overlap(man: pd.DataFrame) -> dict:
    return {
        "val": int(((man["split"] == "val") &
                    (man["start_quarter_idx"] <= TRAIN_END_IDX)).sum()),
        "test": int(((man["split"] == "test") &
                     (man["start_quarter_idx"] < TEST_START_IDX)).sum()),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--embargo", action="store_true",
                    help="drop windows whose quarters straddle a split boundary")
    ap.add_argument("--full", action="store_true")
    main(**vars(ap.parse_args()))
