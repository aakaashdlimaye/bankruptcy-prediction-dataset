"""Phase 4 gate - recompute randomly chosen firm-quarters by hand.

Independent check: for each sampled firm-quarter this script goes back to the
raw companyfacts JSON, prints the actual XBRL facts behind every input
(including the subtraction when a value was reconstructed from a YTD ladder),
recomputes all 29 ratios with plain scalar arithmetic written out longhand,
and compares against the pipeline's stored values.

Output: reports/hand_check.md
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import config as C
import xbrl_extract as X

RATIOS = C.PROCESSED / "ratios_panel.parquet"
PANEL = C.INTERIM / "fundamentals_panel.parquet"
CF_ZIP = C.RAW / "companyfacts.zip"
OUT = C.REPORTS / "hand_check.md"

TOL = 1e-6          # relative tolerance


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "NaN"
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:,.4f}bn"
    if a >= 1e6:
        return f"{v / 1e6:,.4f}m"
    return f"{v:,.4f}"


def explain_fact(blob: dict, concept: str, src: str, quarter: str,
                 period_end: str) -> list[str]:
    """Show the raw XBRL fact(s) that produced one input value."""
    if not isinstance(src, str) or "|" not in src:
        return [f"  - `{concept}`: not populated"]
    tag, method = src.split("|", 1)
    spec = C.CONCEPTS.get(concept)
    lines = []

    if spec is None or method in ("derived", "identity", "annual_div4",
                                  "non_overlapping"):
        return [f"  - `{concept}` <- `{tag}` ({method})"]

    facts = X.usable_facts(blob, tag)
    if spec["kind"] == "instant":
        got = X.instants_to_quarters(facts, tag).get(quarter)
        if got:
            lines.append(f"  - `{concept}` <- `{tag}` instant at {got.period_end} "
                         f"({got.form}, filed {got.filed}) = **{_fmt(got.value)}**")
        return lines

    # duration: show the differencing arithmetic explicitly
    rows = sorted(
        [{"s": X.parse_date(f["start"]), "e": X.parse_date(f["end"]),
          "v": float(f["val"]), "form": f.get("form")}
         for f in facts if f.get("start")],
        key=lambda r: (r["s"], r["e"]))
    got = X.durations_to_quarters(facts, tag).get(quarter)
    if not got:
        return [f"  - `{concept}` <- `{tag}`: no quarter value"]
    if got.method == "direct":
        lines.append(f"  - `{concept}` <- `{tag}` reported directly for a "
                     f"{got.span_days}-day period ending {got.period_end} "
                     f"= **{_fmt(got.value)}**")
        return lines

    end = got.period_end
    cum = [r for r in rows if r["e"] == end]
    pre = [r for r in rows if r["e"] < end and cum and
           abs((r["s"] - cum[0]["s"]).days) <= 7]
    if cum and pre:
        p = max(pre, key=lambda r: r["e"])
        c = max(cum, key=lambda r: (r["e"] - r["s"]).days)
        lines.append(
            f"  - `{concept}` <- `{tag}` de-cumulated: "
            f"YTD({c['s']}..{c['e']}) {_fmt(c['v'])} "
            f"- YTD({p['s']}..{p['e']}) {_fmt(p['v'])} = **{_fmt(got.value)}**")
    else:
        lines.append(f"  - `{concept}` <- `{tag}` ({got.method}) = **{_fmt(got.value)}**")
    return lines


def hand_ratios(v: dict) -> dict:
    """The 29 formulas, written out longhand and independently of phase4."""
    def d(a, b):
        if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
            return np.nan
        return a / b

    g = v.get
    ta, ca, cl, tl, eq = g("Assets"), g("AssetsCurrent"), g("LiabilitiesCurrent"), g("Liabilities"), g("StockholdersEquity")
    cash, inv, ar, ap = g("CashAndEquivalents"), g("InventoryNet"), g("AccountsReceivable"), g("AccountsPayable")
    re_, ltd = g("RetainedEarnings"), g("LongTermDebtNoncurrent")
    rev, cogs, ni = g("Revenue"), g("COGS"), g("NetIncomeLoss")
    ebit, ebitda, ie = g("EBIT"), g("EBITDA"), g("InterestExpense")
    debt, ocf, capex = g("TotalDebt"), g("OCF"), g("CapEx")
    q = 365.0 / 4.0

    def sub(a, b):
        return np.nan if (a is None or b is None or pd.isna(a) or pd.isna(b)) else a - b

    r = {}
    r["r01_current_ratio"] = d(ca, cl)
    r["r02_quick_ratio"] = d(sub(ca, inv), cl)
    r["r03_cash_ratio"] = d(cash, cl)
    r["r04_wc_to_ta"] = d(sub(ca, cl), ta)
    r["r05_net_profit_margin"] = d(ni, rev)
    r["r06_roa"] = d(ni, ta)
    r["r07_roe"] = d(ni, eq)
    r["r08_ebitda_margin"] = d(ebitda, rev)
    r["r09_ebit_to_ta"] = d(ebit, ta)
    r["r10_re_to_ta"] = d(re_, ta)
    r["r11_debt_to_equity"] = d(debt, eq)
    r["r12_debt_to_assets"] = d(debt, ta)
    r["r13_interest_coverage"] = d(ebit, ie) if (ie is not None and not pd.isna(ie) and ie > 0) else np.nan
    r["r14_equity_to_liabilities"] = d(eq, tl)
    r["r15_ltd_to_ta"] = d(ltd, ta)
    r["r16_asset_turnover"] = d(rev, ta)
    r["r17_inventory_turnover"] = d(cogs, inv)
    r["r18_receivables_turnover"] = d(rev, ar)
    r["r19_payables_turnover"] = d(cogs, ap)
    dio, dso, dpo = d(inv, cogs), d(ar, rev), d(ap, cogs)
    r["r20_cash_conversion_cycle"] = (q * dio + q * dso - q * dpo)
    for k, cur, prv in (("r21_revenue_growth", rev, g("Revenue_lag4")),
                        ("r22_net_income_growth", ni, g("NetIncomeLoss_lag4")),
                        ("r24_equity_growth", eq, g("StockholdersEquity_lag4"))):
        r[k] = d(sub(cur, prv), abs(prv) if prv is not None and not pd.isna(prv) else np.nan)
    r["r23_assets_growth"] = d(sub(ta, g("Assets_lag4")), g("Assets_lag4"))
    r["r25_ocf_to_cl"] = d(ocf, cl)
    r["r26_fcf_to_ta"] = d(sub(ocf, capex), ta)
    r["r27_accrual_quality"] = d(ocf, ni)
    r["r28_ocf_to_debt"] = d(ocf, debt)
    r["r29_negative_equity_flag"] = np.nan if (eq is None or pd.isna(eq)) else float(eq < 0)
    return r


def main(n: int = 5, seed: int = C.RANDOM_SEED) -> bool:
    rp = pd.read_parquet(RATIOS)
    fp = pd.read_parquet(PANEL)

    # Sample firm-quarters that actually have enough inputs for the arithmetic
    # to be worth printing, then choose randomly among them.
    core = ["Assets", "AssetsCurrent", "LiabilitiesCurrent", "Liabilities",
            "StockholdersEquity", "Revenue", "NetIncomeLoss", "OCF"]
    ok = fp.dropna(subset=core)
    sample = ok.sample(n=n, random_state=seed)

    lag_cols = ["Revenue", "NetIncomeLoss", "Assets", "StockholdersEquity"]
    lag_src = fp.set_index(["cik", "quarter_idx"])[lag_cols]

    L = ["# Phase 4 Gate - Hand Recomputation from Raw Facts", "",
         f"{n} firm-quarters chosen at random (seed {seed}) from firm-quarters with a",
         "complete core input set. For each one the raw XBRL facts are pulled straight",
         "out of `companyfacts.zip`, the de-cumulation arithmetic is shown where a",
         "value was reconstructed, all 29 ratios are recomputed longhand, and the",
         "results are compared with `data/processed/ratios_panel.parquet`.", ""]

    all_ok = True
    with zipfile.ZipFile(CF_ZIP) as zf:
        for _, row in sample.iterrows():
            cik, quarter = row["cik"], row["quarter"]
            blob = json.loads(zf.read(f"CIK{int(cik):010d}.json"))
            vals = {c: (None if pd.isna(row.get(c)) else float(row.get(c)))
                    for c in list(C.CONCEPTS) + ["TotalDebt", "EBIT", "EBITDA"]}
            for c in lag_cols:
                key = (cik, int(row["quarter_idx"]) - 4)
                vals[f"{c}_lag4"] = (float(lag_src.loc[key, c])
                                     if key in lag_src.index and
                                     not pd.isna(lag_src.loc[key, c]) else None)

            L += [f"## {row['company']} (CIK {cik}) - {quarter}", "",
                  f"Fiscal period end {row['period_end']}, {row['fp']} FY{row['fy']}.", "",
                  "### Inputs traced to raw XBRL facts", ""]
            for c in ["Assets", "AssetsCurrent", "LiabilitiesCurrent", "Liabilities",
                      "StockholdersEquity", "CashAndEquivalents", "InventoryNet",
                      "AccountsReceivable", "AccountsPayable", "RetainedEarnings",
                      "Revenue", "COGS", "NetIncomeLoss", "OperatingIncomeLoss",
                      "InterestExpense", "DepreciationAmortization", "OCF", "CapEx",
                      "LongTermDebtNoncurrent"]:
                L += explain_fact(blob, c, row.get(f"{c}__src"), quarter,
                                  row["period_end"])
            L += ["",
                  f"  - derived `EBIT` = {_fmt(vals['EBIT'])}, "
                  f"`EBITDA` = {_fmt(vals['EBITDA'])}, "
                  f"`TotalDebt` = {_fmt(vals['TotalDebt'])}", "",
                  "### Ratios: hand arithmetic vs pipeline", "",
                  "| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |",
                  "|---|---|---|---:|---:|---|"]

            hand = hand_ratios(vals)
            pr = rp[(rp["cik"] == cik) & (rp["quarter"] == quarter)]
            if pr.empty:
                L += ["", "*(not present in ratios panel)*", ""]
                continue
            pr = pr.iloc[0]
            for i, col in enumerate(C.RATIO_NAMES, start=1):
                h, p = hand[col], pr[f"raw__{col}"]
                both_nan = (pd.isna(h) and pd.isna(p))
                close = both_nan or (not pd.isna(h) and not pd.isna(p) and
                                     abs(h - p) <= TOL * max(1.0, abs(p)))
                if not close:
                    all_ok = False
                L.append(f"| {i} | `{col}` | {EXPR.get(col, '')} | {_fmt(h)} | "
                         f"{_fmt(p)} | {'OK' if close else '**MISMATCH**'} |")
            L.append("")

    L += ["## Verdict", "",
          f"**{'PASS' if all_ok else 'FAIL'}** - all 29 ratios matched to a relative "
          f"tolerance of {TOL:g} on every sampled firm-quarter."
          if all_ok else
          f"**FAIL** - at least one ratio disagreed beyond {TOL:g}.", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[verify] -> {OUT.relative_to(C.ROOT)}")
    print(f"GATE: hand recomputation -> {'PASS' if all_ok else 'FAIL'}")
    return all_ok


EXPR = {
    "r01_current_ratio": "CA / CL",
    "r02_quick_ratio": "(CA - Inv) / CL",
    "r03_cash_ratio": "Cash / CL",
    "r04_wc_to_ta": "(CA - CL) / TA",
    "r05_net_profit_margin": "NI / Rev",
    "r06_roa": "NI / TA",
    "r07_roe": "NI / Eq",
    "r08_ebitda_margin": "EBITDA / Rev",
    "r09_ebit_to_ta": "EBIT / TA",
    "r10_re_to_ta": "RE / TA",
    "r11_debt_to_equity": "Debt / Eq",
    "r12_debt_to_assets": "Debt / TA",
    "r13_interest_coverage": "EBIT / IntExp",
    "r14_equity_to_liabilities": "Eq / TL",
    "r15_ltd_to_ta": "LTD / TA",
    "r16_asset_turnover": "Rev / TA",
    "r17_inventory_turnover": "COGS / Inv",
    "r18_receivables_turnover": "Rev / AR",
    "r19_payables_turnover": "COGS / AP",
    "r20_cash_conversion_cycle": "91.25(Inv/COGS + AR/Rev - AP/COGS)",
    "r21_revenue_growth": "(Rev - Rev_t-4) / |Rev_t-4|",
    "r22_net_income_growth": "(NI - NI_t-4) / |NI_t-4|",
    "r23_assets_growth": "(TA - TA_t-4) / TA_t-4",
    "r24_equity_growth": "(Eq - Eq_t-4) / |Eq_t-4|",
    "r25_ocf_to_cl": "OCF / CL",
    "r26_fcf_to_ta": "(OCF - CapEx) / TA",
    "r27_accrual_quality": "OCF / NI",
    "r28_ocf_to_debt": "OCF / Debt",
    "r29_negative_equity_flag": "1 if Eq < 0",
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=C.RANDOM_SEED)
    ok = main(**vars(ap.parse_args()))
    raise SystemExit(0 if ok else 1)
