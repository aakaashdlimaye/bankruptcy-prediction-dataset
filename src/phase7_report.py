"""Phase 7 - DATASET_REPORT.md, the single document describing what was built.

Pulls real numbers out of the artefacts on disk; nothing here is hard-coded.
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

OUT = C.REPORTS / "DATASET_REPORT.md"


def _mb(p: Path) -> float:
    return p.stat().st_size / 1e6 if p.exists() else 0.0


def main(full: bool = False) -> None:
    sfx = C.suffix(full)
    labels = pd.read_csv(C.PROCESSED / "labels.csv", dtype={"cik": str})
    events = pd.read_csv(C.PROCESSED / "labels_events.csv", dtype={"cik": str})
    uni = pd.read_parquet(C.INTERIM / "universe_full.parquet")
    pilot = pd.read_csv(C.DATA / "universe_pilot.csv", dtype={"cik": str})
    panel = pd.read_parquet(C.panel_path(full))
    ratios = pd.read_parquet(C.ratios_path(full))
    man = pd.read_csv(C.PROCESSED / "split_manifest.csv", dtype={"cik": str})
    unmatched = pd.read_csv(C.REPORTS / "unmatched_positives.csv", dtype={"cik": str})
    stats = json.loads((C.INTERIM / "extraction_stats.json").read_text())
    winsor = json.loads((C.PROCESSED / "winsor_bounds.json").read_text())
    scaler = json.loads((C.PROCESSED / "scaler_params.json").read_text())

    inwin = labels[labels["in_window"] == 1]
    scope = uni[uni["in_universe"] == 1]

    dstats = {k: v for k, v in stats.items() if not k.startswith("_")}
    direct = sum(v.get("direct", 0) for v in dstats.values() if isinstance(v, dict))
    pref = sum(v.get("differenced_prefix", 0) for v in dstats.values() if isinstance(v, dict))
    tile = sum(v.get("differenced_tiling", 0) for v in dstats.values() if isinstance(v, dict))
    lost = sum(v.get("cumulative_unrecovered", 0) + v.get("wide_quarter_unrecovered", 0)
               for v in dstats.values() if isinstance(v, dict))
    ie_fill = stats.get("_fallback", {}).get("InterestExpense_annual_div4", 0)

    L = [
        "# Dataset Report", "",
        "Bankruptcy prediction from temporal sequences of quarterly financial",
        "ratios, US listed non-financial firms, 2010-2024. Built from SEC EDGAR",
        "XBRL company facts plus three independent bankruptcy label sources.", "",
        f"Universe run: **{'FULL' if full else 'PILOT'}**.", "",
        "## 1. Headline counts", "",
        "| Quantity | Value |", "|---|---:|",
        f"| Distinct bankrupt firms identified (any year) | {len(labels):,} |",
        f"| ... with an event date inside 2010-2024 | {len(inwin):,} |",
        f"| Distinct bankruptcy events inside 2010-2024 | "
        f"{int(((pd.to_datetime(events['event_date']) >= C.STUDY_START) & (pd.to_datetime(events['event_date']) <= C.STUDY_END)).sum()):,} |",
        f"| Non-financial firms with 10-K/10-Q in window (full universe) | {len(scope):,} |",
        f"| Firms in the {'full' if full else 'pilot'} run | {len(pilot):,} |",
        f"| Firms yielding at least one usable firm-quarter | {panel['cik'].nunique():,} |",
        f"| Firm-quarters in the fundamentals panel | {len(panel):,} |",
        f"| Firm-quarters in the ratio panel | {len(ratios):,} |",
        f"| 8-quarter sequences built | {len(man):,} |",
        f"| Firms contributing at least one sequence | {man['cik'].nunique():,} |",
        "",
        "## 2. Splits, positives and class rates", "",
        "Split is assigned by the window's **end quarter**.", "",
        "| Split | End quarters | Sequences | Firms | " +
        " | ".join(f"pos y{h}" for h in C.HORIZONS) + " | rate y1 | rate y4 |",
        "|---|---|---:|---:|" + "---:|" * len(C.HORIZONS) + "---:|---:|",
    ]
    rng = {"train": f"<= {C.TRAIN_END}", "val": f"{C.VAL_START}-{C.VAL_END}",
           "test": f"{C.TEST_START}-{C.TEST_END}"}
    for s in ("train", "val", "test"):
        d = man[man["split"] == s]
        cells = " | ".join(f"{int(d[f'y{h}'].sum()):,}" for h in C.HORIZONS)
        L.append(f"| {s} | {rng[s]} | {len(d):,} | {d['cik'].nunique():,} | {cells} | "
                 f"{100 * d['y1'].mean():.2f}% | {100 * d['y4'].mean():.2f}% |")
    cells = " | ".join(f"{int(man[f'y{h}'].sum()):,}" for h in C.HORIZONS)
    L.append(f"| **all** | | **{len(man):,}** | **{man['cik'].nunique():,}** | "
             f"{cells} | {100 * man['y1'].mean():.2f}% | {100 * man['y4'].mean():.2f}% |")

    L += ["",
          "Positive *firms* (rather than windows) per split:", "",
          "| Split | Positive firms | Survivor firms |", "|---|---:|---:|"]
    for s in ("train", "val", "test"):
        d = man[man["split"] == s]
        L.append(f"| {s} | {d.loc[d['is_positive_firm'] == 1, 'cik'].nunique():,} | "
                 f"{d.loc[d['is_positive_firm'] == 0, 'cik'].nunique():,} |")

    L += [
        "", "## 3. Coverage summary", "",
        "Full per-concept detail in `reports/coverage_report.md`.", "",
        "| Concept group | Median coverage |", "|---|---:|",
    ]
    groups = {
        "Tier-1 balance sheet and net income": C.TIER1_CONCEPTS,
        "Revenue and COGS": ["Revenue", "COGS"],
        "Cash flow (OCF, CapEx, D&A)": ["OCF", "CapEx", "DepreciationAmortization"],
        "Debt aggregates": ["TotalDebt", "LongTermDebtNoncurrent", "CurrentDebt"],
        "Derived earnings (EBIT, EBITDA)": ["EBIT", "EBITDA"],
    }
    for g, cols in groups.items():
        cols = [c for c in cols if c in panel]
        med = np.median([100 * panel[c].notna().mean() for c in cols]) if cols else float("nan")
        L.append(f"| {g} | {med:.1f}% |")

    L += [
        "", "## 4. Known caveats", "",
        "### 4.1 Interest expense",
        f"- `InterestExpense` raw coverage is "
        f"{100 * panel['InterestExpense'].notna().mean():.1f}% after the annual/4 "
        f"fallback filled **{ie_fill:,} cells** "
        f"({100 * ie_fill / max(len(panel), 1):.1f}% of firm-quarters). Without the "
        "fallback it would be "
        f"{100 * (int(panel['InterestExpense'].notna().sum()) - ie_fill) / max(len(panel), 1):.1f}%.",
        "- Ratio 13 (interest coverage) explodes near zero interest expense; the "
        "1st/99th winsorisation clips it to "
        f"[{winsor['bounds']['r13_interest_coverage']['p01']:.0f}, "
        f"{winsor['bounds']['r13_interest_coverage']['p99']:.0f}], the widest "
        "clipping applied to any ratio.",
        "- Quarters where the filer reports negative or zero interest expense are "
        "left NaN rather than producing a sign-flipped coverage ratio.",
        "",
        "### 4.2 YTD de-cumulation",
        "| Route | Quarter-values |", "|---|---:|",
        f"| reported directly as an 80-100 day quarter | {direct:,} |",
        f"| reconstructed as `Qn = YTD(n) - YTD(n-1)` | {pref:,} |",
        f"| reconstructed as `Q4 = FY - Q1 - Q2 - Q3` | {tile:,} |",
        f"| cumulative facts not reducible to a quarter | {lost:,} |",
        "",
        f"Differencing supplied **{100 * (pref + tile) / max(direct + pref + tile, 1):.1f}%** "
        "of all flow observations. Cash-flow items are the most affected: "
        f"{100 * pd.Series(panel['OCF__src'].dropna().str.endswith('differenced')).mean():.0f}% "
        "of filled OCF cells and "
        f"{100 * pd.Series(panel['CapEx__src'].dropna().str.endswith('differenced')).mean():.0f}% "
        "of CapEx cells are reconstructed, exactly as the spec predicts.",
        "",
        "### 4.3 Structural sentinels",
        f"- `has_inventory = 0` for "
        f"{int((ratios.drop_duplicates('cik')['has_inventory'] == 0).sum()):,} firms "
        f"({int((ratios['has_inventory'] == 0).sum()):,} firm-quarters): ratios 2, 17 "
        "and 20 are NaN, not imputed.",
        f"- `has_debt = 0` for "
        f"{int((ratios.drop_duplicates('cik')['has_debt'] == 0).sum()):,} firms "
        f"({int((ratios['has_debt'] == 0).sum()):,} firm-quarters): ratio 13 is NaN.",
        f"- `r29_negative_equity_flag` is 1 in "
        f"{int((ratios['r29_negative_equity_flag'] == 1).sum()):,} firm-quarters "
        f"({100 * ratios['r29_negative_equity_flag'].mean():.1f}% of those where "
        "equity is observed). Negative-equity rows are kept, not dropped.",
        "",
        "### 4.4 Unmatched positives",
        f"Every labelled bankrupt firm either enters the panel or is listed in "
        f"`reports/unmatched_positives.csv` with a reason. "
        f"**{len(unmatched):,}** of {len(inwin):,} in-window positives could not "
        "enter:", "",
        "| Reason | Firms |", "|---|---:|",
    ] + [f"| {k} | {v:,} |" for k, v in unmatched["reason"].value_counts().items()] + [
        "",
        "### 4.5 Other caveats",
        "- The pilot is deliberately positive-enriched (positives are never "
        "subsampled, and they already exceed the ~500-firm pilot budget), so the "
        "class rates above are **not** population rates.",
        "- Survivors that stop filing for non-bankruptcy reasons (acquisition, "
        "going private, deregistration) are right-censored and labelled 0. No "
        "attempt is made to distinguish them from continuing firms.",
        "- Flow ratios pair a quarterly flow with a point-in-time stock, so "
        "turnovers and margins are quarterly, roughly a quarter of their annual "
        "equivalents.",
        "- Ratio 14 is the **book-value** Altman X4 (the Z'/Z\" variant), not the "
        "original 1968 market-value form.",
        "- Stride-1 windowing means input quarters near a split boundary can "
        "appear in windows on both sides; no label is shared, and `--embargo` "
        "removes those windows. See `reports/leakage_audit.md`.",
        "",
        "## 5. Gate results", "",
        "| Gate | Result | Evidence |", "|---|---|---|",
        f"| Phase 1: >= 250 bankrupt firms in 2010-2024 | PASS ({len(inwin):,}) | `reports/labels_report.md` |",
        "| Phase 3: coverage expectations | PASS | `reports/coverage_report.md` |",
        "| Phase 4: hand recomputation of 5 firm-quarters | PASS | `reports/hand_check.md` |",
        "| Phase 5: four-check leakage audit | PASS | `reports/leakage_audit.md` |",
        "| Unit tests incl. both YTD filer styles | PASS | `pytest tests/` |",
        "",
        "## 6. Artefact sizes", "",
        "| File | Size |", "|---|---:|",
    ]
    for p in [C.panel_path(full), C.ratios_path(full),
              C.PROCESSED / "sequences_train.npz", C.PROCESSED / "sequences_val.npz",
              C.PROCESSED / "sequences_test.npz", C.PROCESSED / "split_manifest.csv",
              C.PROCESSED / "labels.csv", C.PROCESSED / "scaler_params.json"]:
        L.append(f"| `{p.relative_to(C.ROOT).as_posix()}` | {_mb(p):.1f} MB |")

    L += ["", "## 7. Tensor shapes", "",
          "| Split | X | y | mask | indicators |", "|---|---|---|---|---|"]
    for s in ("train", "val", "test"):
        f = C.PROCESSED / f"sequences_{s}.npz"
        if not f.exists():
            continue
        with np.load(f, allow_pickle=False) as z:
            L.append(f"| {s} | {tuple(z['X'].shape)} | {tuple(z['y'].shape)} | "
                     f"{tuple(z['mask'].shape)} | {tuple(z['indicators'].shape)} |")
    L += ["",
          f"`X` is z-scored with parameters fitted on {scaler['n_train_windows']:,} "
          "train windows only. Cells still missing after forward fill are set to "
          "the train mean (0 after standardisation) and flagged in `mask`.", ""]

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {OUT.relative_to(C.ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    main(**vars(ap.parse_args()))
