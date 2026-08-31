"""Phase 4 - The 28 ratios plus the negative-equity flag.

Formulas follow `Capstone Summary.md` section 5 exactly. Three rules beyond
the arithmetic:

* **Undefined is not missing.** A firm with no inventory has no quick ratio,
  inventory turnover or cash conversion cycle to compute; a firm with no debt
  has no interest coverage. Those cells are NaN and the fact is carried in the
  `has_inventory` / `has_debt` indicator columns, never imputed to a number the
  model would learn as real.
* **Growth is year-over-year**, t against t-4, matched on quarter index within
  the same firm so a gap in the panel cannot silently become a t-1 comparison.
* **Winsorisation is fitted on the training period only** (period end
  <= 2019-12-31) and applied to every period. This is a leakage rule.

Outputs: data/processed/ratios_panel.parquet, reports/ratios_report.md
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

WINSOR_OUT = C.PROCESSED / "winsor_bounds.json"
REPORT = C.REPORTS / "ratios_report.md"

DAYS_PER_QUARTER = 365.0 / 4.0        # 91.25; documented in DECISIONS.md
STRUCTURAL_LOOKBACK = 8               # "8 most recent quarters" per the spec
STRUCTURAL_ABSENT_MIN = 6             # absent in >= 6 of them => structurally absent


def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    """Elementwise division; NaN wherever the denominator is zero or missing."""
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    out = num / den.where(den != 0)
    return out.replace([np.inf, -np.inf], np.nan)


# ---------------------------------------------------------------------------
# Structural indicators
# ---------------------------------------------------------------------------
def structural_indicators(p: pd.DataFrame) -> pd.DataFrame:
    """has_inventory / has_debt, decided per firm over its 8 most recent quarters."""
    p = p.sort_values(["cik", "quarter_idx"])
    ind = {}

    tail = p.groupby("cik").tail(STRUCTURAL_LOOKBACK)
    inv_absent = tail["InventoryNet"].isna() | (tail["InventoryNet"] == 0)
    n_absent = inv_absent.groupby(tail["cik"]).sum()
    n_seen = inv_absent.groupby(tail["cik"]).size()
    # Firms with fewer than 8 quarters: scale the threshold proportionally.
    thresh = (STRUCTURAL_ABSENT_MIN / STRUCTURAL_LOOKBACK) * n_seen
    ind["has_inventory"] = (~(n_absent >= thresh)).astype(int)

    # A firm has debt if it ever reports positive total debt or positive
    # interest expense anywhere in its history. Using only the recent-quarter
    # rule would misread the many filers who tag debt annually.
    ever_debt = p.groupby("cik")["TotalDebt"].max()
    ever_int = p.groupby("cik")["InterestExpense"].max()
    ind["has_debt"] = ((ever_debt.fillna(0) > 0) | (ever_int.fillna(0) > 0)).astype(int)

    out = pd.DataFrame(ind)
    out.index.name = "cik"
    return out.reset_index()


# ---------------------------------------------------------------------------
# Ratio computation
# ---------------------------------------------------------------------------
def compute_ratios(p: pd.DataFrame) -> pd.DataFrame:
    p = p.sort_values(["cik", "quarter_idx"]).reset_index(drop=True)

    ta, ca, cl = p["Assets"], p["AssetsCurrent"], p["LiabilitiesCurrent"]
    tl, eq, cash = p["Liabilities"], p["StockholdersEquity"], p["CashAndEquivalents"]
    inv, ar, ap = p["InventoryNet"], p["AccountsReceivable"], p["AccountsPayable"]
    re_, ltd = p["RetainedEarnings"], p["LongTermDebtNoncurrent"]
    rev, cogs, ni = p["Revenue"], p["COGS"], p["NetIncomeLoss"]
    ebit, ebitda, ie = p["EBIT"], p["EBITDA"], p["InterestExpense"]
    debt, ocf, capex = p["TotalDebt"], p["OCF"], p["CapEx"]

    r = pd.DataFrame(index=p.index)
    # --- Liquidity ---------------------------------------------------------
    r["r01_current_ratio"] = safe_div(ca, cl)
    r["r02_quick_ratio"] = safe_div(ca - inv, cl)
    r["r03_cash_ratio"] = safe_div(cash, cl)
    r["r04_wc_to_ta"] = safe_div(ca - cl, ta)
    # --- Profitability -----------------------------------------------------
    r["r05_net_profit_margin"] = safe_div(ni, rev)
    r["r06_roa"] = safe_div(ni, ta)
    r["r07_roe"] = safe_div(ni, eq)          # negative equity kept as-is
    r["r08_ebitda_margin"] = safe_div(ebitda, rev)
    r["r09_ebit_to_ta"] = safe_div(ebit, ta)
    r["r10_re_to_ta"] = safe_div(re_, ta)    # accumulated deficits stay negative
    # --- Leverage ----------------------------------------------------------
    r["r11_debt_to_equity"] = safe_div(debt, eq)
    r["r12_debt_to_assets"] = safe_div(debt, ta)
    r["r13_interest_coverage"] = safe_div(ebit, ie.where(ie > 0))
    r["r14_equity_to_liabilities"] = safe_div(eq, tl)   # book-value Z'/Z" form
    r["r15_ltd_to_ta"] = safe_div(ltd, ta)
    # --- Efficiency --------------------------------------------------------
    r["r16_asset_turnover"] = safe_div(rev, ta)
    r["r17_inventory_turnover"] = safe_div(cogs, inv)
    r["r18_receivables_turnover"] = safe_div(rev, ar)
    r["r19_payables_turnover"] = safe_div(cogs, ap)
    dio = safe_div(inv * DAYS_PER_QUARTER, cogs)
    dso = safe_div(ar * DAYS_PER_QUARTER, rev)
    dpo = safe_div(ap * DAYS_PER_QUARTER, cogs)
    r["r20_cash_conversion_cycle"] = dio + dso - dpo
    # --- Growth (t vs t-4, matched on quarter index within firm) -----------
    lag = _lag4(p, ["Revenue", "NetIncomeLoss", "Assets", "StockholdersEquity"])
    r["r21_revenue_growth"] = safe_div(rev - lag["Revenue"], lag["Revenue"].abs())
    r["r22_net_income_growth"] = safe_div(ni - lag["NetIncomeLoss"],
                                          lag["NetIncomeLoss"].abs())
    r["r23_assets_growth"] = safe_div(ta - lag["Assets"], lag["Assets"])
    r["r24_equity_growth"] = safe_div(eq - lag["StockholdersEquity"],
                                      lag["StockholdersEquity"].abs())
    # --- Cash flow ---------------------------------------------------------
    r["r25_ocf_to_cl"] = safe_div(ocf, cl)
    r["r26_fcf_to_ta"] = safe_div(ocf - capex, ta)
    r["r27_accrual_quality"] = safe_div(ocf, ni)
    r["r28_ocf_to_debt"] = safe_div(ocf, debt)
    # --- Feature 29 --------------------------------------------------------
    r["r29_negative_equity_flag"] = np.where(eq.isna(), np.nan, (eq < 0).astype(float))

    return r


def _lag4(p: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Value at t-4 for the same firm, matched on quarter index, not position."""
    src = p[["cik", "quarter_idx"] + cols].copy()
    src["quarter_idx"] = src["quarter_idx"] + 4
    merged = p[["cik", "quarter_idx"]].merge(
        src, on=["cik", "quarter_idx"], how="left", suffixes=("", "_lag"))
    return merged[cols].set_axis(p.index)


def apply_structural_rules(r: pd.DataFrame, p: pd.DataFrame,
                           ind: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    m = p[["cik"]].merge(ind, on="cik", how="left")
    has_inv = m["has_inventory"].fillna(1).to_numpy().astype(bool)
    has_debt = m["has_debt"].fillna(1).to_numpy().astype(bool)

    counts = {}
    for col in C.INVENTORY_RATIOS:
        before = int(r[col].notna().sum())
        r.loc[~has_inv, col] = np.nan
        counts[col] = before - int(r[col].notna().sum())
    for col in C.DEBT_RATIOS:
        before = int(r[col].notna().sum())
        r.loc[~has_debt, col] = np.nan
        counts[col] = before - int(r[col].notna().sum())

    stats = {
        "firms_without_inventory": int((ind["has_inventory"] == 0).sum()),
        "firms_with_inventory": int((ind["has_inventory"] == 1).sum()),
        "firms_without_debt": int((ind["has_debt"] == 0).sum()),
        "firms_with_debt": int((ind["has_debt"] == 1).sum()),
        "rows_no_inventory": int((~has_inv).sum()),
        "rows_no_debt": int((~has_debt).sum()),
        "cells_set_undefined": counts,
    }
    return r, stats


# ---------------------------------------------------------------------------
# Winsorisation (train-period fit, all-period apply)
# ---------------------------------------------------------------------------
def winsorise(r: pd.DataFrame, p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    train = pd.to_datetime(p["period_end"]) <= pd.Timestamp(C.TRAIN_CUTOFF_DATE)
    bounds: dict[str, dict] = {}
    out = r.copy()
    for col in C.RATIO_NAMES:
        if col in C.NO_WINSORISE:
            continue
        s = r.loc[train.to_numpy(), col]
        lo, hi = s.quantile(0.01), s.quantile(0.99)
        if pd.isna(lo) or pd.isna(hi):
            continue
        bounds[col] = {"p01": float(lo), "p99": float(hi),
                       "n_train_obs": int(s.notna().sum())}
        out[col] = r[col].clip(lower=lo, upper=hi)
    meta = {
        "fitted_on": f"period_end <= {C.TRAIN_CUTOFF_DATE}",
        "n_train_rows": int(train.sum()),
        "n_total_rows": int(len(r)),
        "excluded_from_winsorisation": sorted(C.NO_WINSORISE),
        "bounds": bounds,
    }
    return out, meta


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(p: pd.DataFrame, raw: pd.DataFrame, win: pd.DataFrame,
                 meta: dict, sstats: dict) -> None:
    n = len(p)
    L = [
        "# Phase 4 - Ratios Report", "",
        f"Panel: **{n:,} firm-quarters**, **{p['cik'].nunique():,} firms**, "
        f"{p['quarter'].min()} to {p['quarter'].max()}.", "",
        "## Per-ratio distributions, before and after winsorisation", "",
        "Winsorisation bounds are the 1st/99th percentiles of the **training period "
        f"only** ({meta['fitted_on']}, {meta['n_train_rows']:,} rows), applied to all "
        "periods.", "",
        "| # | Ratio | Non-null | Cov % | Raw min | Raw p50 | Raw max | p01 bound | p99 bound | Clipped |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, col in enumerate(C.RATIO_NAMES, start=1):
        s, w = raw[col], win[col]
        b = meta["bounds"].get(col)
        clipped = int((s.notna() & (s != w)).sum()) if b else 0
        L.append(
            f"| {i} | `{col}` | {int(s.notna().sum()):,} | {100 * s.notna().mean():.1f} | "
            f"{_f(s.min())} | {_f(s.median())} | {_f(s.max())} | "
            f"{_f(b['p01']) if b else 'n/a'} | {_f(b['p99']) if b else 'n/a'} | "
            f"{clipped:,} |")

    # missingness heatmap: ratio x year
    yr = p["quarter"].str[:4]
    years = sorted(yr.unique())
    L += ["", "## Missingness heatmap - % missing by ratio and year", "",
          "| Ratio | " + " | ".join(years) + " |",
          "|---|" + "---:|" * len(years)]
    for col in C.RATIO_NAMES:
        cells = []
        for y in years:
            m = win.loc[(yr == y).to_numpy(), col]
            cells.append(f"{100 * m.isna().mean():.0f}")
        L.append(f"| `{col}` | " + " | ".join(cells) + " |")

    cs = sstats["cells_set_undefined"]
    L += [
        "", "## Undefined vs missing", "",
        "Structurally undefined cells are NaN and flagged, never imputed.", "",
        "| Indicator | Firms = 1 | Firms = 0 | Firm-quarters = 0 |",
        "|---|---:|---:|---:|",
        f"| `has_inventory` | {sstats['firms_with_inventory']:,} | "
        f"{sstats['firms_without_inventory']:,} | {sstats['rows_no_inventory']:,} |",
        f"| `has_debt` | {sstats['firms_with_debt']:,} | "
        f"{sstats['firms_without_debt']:,} | {sstats['rows_no_debt']:,} |",
        "",
        "| Ratio set undefined | Cells cleared |", "|---|---:|",
    ] + [f"| `{k}` | {v:,} |" for k, v in cs.items()] + [
        "",
        "`has_inventory` is 0 when inventory is absent or zero in at least 6 of the",
        "firm's 8 most recent quarters, per the spec. `has_debt` is 0 when the firm",
        "never reports positive total debt or positive interest expense anywhere in",
        "its history - a recent-quarters rule would misread the many filers who tag",
        "debt only annually.", "",
        "## Conventions", "",
        f"- Flow ratios pair a **quarterly** flow with a point-in-time stock, so "
        f"asset turnover, margins and turnovers are quarterly, roughly a quarter of "
        f"their annual equivalents.",
        f"- Cash conversion cycle uses a quarter of {DAYS_PER_QUARTER:.2f} days: "
        f"DIO = {DAYS_PER_QUARTER:.2f} x Inventory / COGS, DSO = "
        f"{DAYS_PER_QUARTER:.2f} x AR / Revenue, DPO = {DAYS_PER_QUARTER:.2f} x AP / COGS.",
        "- Ratio 14 uses **book** equity over total liabilities: this is the Z'/Z\"",
        "  variant of Altman X4, not the original 1968 market-value form.",
        "- `RetainedEarningsAccumulatedDeficit` negatives are kept as reported.",
        "- ROE and debt-to-equity are computed as-is at negative equity and left to",
        "  winsorisation; `r29_negative_equity_flag` carries the signal explicitly and",
        "  is excluded from winsorisation because it is binary.", "",
    ]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {REPORT.relative_to(C.ROOT)}")


def _f(v) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v))):
        return "-"
    a = abs(v)
    if a >= 1e6 or (a < 1e-3 and a > 0):
        return f"{v:.2e}"
    return f"{v:,.3f}"


def main(force: bool = False, full: bool = False) -> pd.DataFrame:
    PANEL_IN, RATIOS_OUT = C.panel_path(full), C.ratios_path(full)
    print("=" * 70)
    print("PHASE 4 - RATIO COMPUTATION")
    print("=" * 70)
    p = pd.read_parquet(PANEL_IN).sort_values(["cik", "quarter_idx"]).reset_index(drop=True)

    ind = structural_indicators(p)
    raw = compute_ratios(p)
    raw, sstats = apply_structural_rules(raw, p, ind)
    win, meta = winsorise(raw, p)

    out = pd.concat([
        p[["cik", "company", "sic", "is_bankrupt", "quarter", "quarter_idx",
           "period_end", "fy", "fp"]].reset_index(drop=True),
        win.reset_index(drop=True),
        raw.add_prefix("raw__").reset_index(drop=True),
    ], axis=1)
    out = out.merge(ind, on="cik", how="left")
    out["has_inventory"] = out["has_inventory"].fillna(1).astype(int)
    out["has_debt"] = out["has_debt"].fillna(1).astype(int)

    out.to_parquet(RATIOS_OUT, index=False)
    WINSOR_OUT.write_text(json.dumps(meta, indent=2))
    print(f"[ratios] {len(out):,} firm-quarters x {len(C.RATIO_NAMES)} ratios "
          f"-> {RATIOS_OUT.relative_to(C.ROOT)}")
    print(f"[ratios] winsorisation bounds -> {WINSOR_OUT.relative_to(C.ROOT)}")

    write_report(p, raw, win, meta, sstats)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--full", action="store_true")
    main(**vars(ap.parse_args()))
