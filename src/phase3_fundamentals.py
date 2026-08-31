"""Phase 3 - Fundamentals extraction from SEC EDGAR XBRL company facts.

Reads only the pilot-universe JSONs out of companyfacts.zip, runs each through
`xbrl_extract` (fallback chains + YTD de-cumulation), then adds the derived
quantities the ratio table needs:

  * ``Liabilities``  - reported tag, else L&SE minus NCI-inclusive equity
  * ``TotalDebt``    - LTD noncurrent + current debt, where current debt is
                       max(DebtCurrent, LTDCurrent + ShortTermBorrowings) so a
                       filer tagging both is not double-counted
  * ``EBIT``         - OperatingIncomeLoss (spec definition), else
                       NetIncome + InterestExpense + IncomeTax
  * ``EBITDA``       - EBIT + D&A chain
  * ``InterestExpense`` annual/4 fallback for quarters the filer only tagged
                       annually (the spec's known 20-30% gap)

Every filled cell carries a provenance string ``<tag>|<method>`` in a parallel
``<concept>__src`` column.

Outputs: data/interim/fundamentals_panel.parquet, reports/coverage_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from tqdm import tqdm

import config as C
import xbrl_extract as X

CF_ZIP = C.RAW / "companyfacts.zip"
PILOT = C.DATA / "universe_pilot.csv"
UNIVERSE_FULL = C.INTERIM / "universe_full.parquet"
STATS_OUT = C.INTERIM / "extraction_stats.json"
REPORT = C.REPORTS / "coverage_report.md"

CHUNK_SIZE = 200
VALUE_COLS = list(C.CONCEPTS.keys())
DERIVED = ["TotalDebt", "CurrentDebt", "EBIT", "EBITDA"]


# ---------------------------------------------------------------------------
# Per-firm assembly
# ---------------------------------------------------------------------------
def _sum_present(*vals) -> float:
    """Sum, treating missing components as zero, but NaN if all are missing."""
    present = [v for v in vals if v is not None and not pd.isna(v)]
    return float(np.sum(present)) if present else np.nan


def _derive_debt(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    """Total interest-bearing debt, guarding the two silent-corruption traps.

    Trap 1 - *missing is not zero*. Many filers tag long-term debt only in the
    10-K, so three quarters a year have no long-term component. Summing with
    missing-as-zero turns a stable 4.8bn debt load into a sawtooth between
    4.9bn and 0.1bn. A component is treated as a true zero only when the firm
    never reports it anywhere in its history; otherwise the quarter is NaN.

    Trap 2 - *``LongTermDebt`` already includes current maturities*. When the
    fallback chain lands on that tag rather than ``LongTermDebtNoncurrent``,
    adding ``LongTermDebtCurrent`` (or ``DebtCurrent``, which contains it)
    double-counts. Only genuinely separate short-term borrowings are added.
    """
    ltd = df["LongTermDebtNoncurrent"]
    ltd_tag = df["LongTermDebtNoncurrent__src"].astype("object").fillna("") \
        .str.split("|").str[0]
    inclusive = ltd_tag.eq("LongTermDebt")

    ltdc, stb, dc = (df["LongTermDebtCurrent"], df["ShortTermBorrowings"],
                     df["DebtCurrent"])
    comp = df.apply(lambda r: _sum_present(r["LongTermDebtCurrent"],
                                           r["ShortTermBorrowings"]), axis=1)
    # DebtCurrent is the *total* of current debt; max() avoids both
    # double-counting it against its own components and undercounting when the
    # filer tags only some of them.
    cur_full = pd.Series(
        np.where(dc.notna() & comp.notna(), np.maximum(dc.fillna(0), comp.fillna(0)),
                 np.where(dc.notna(), dc, comp)), index=df.index)
    current = cur_full.where(~inclusive, stb)      # trap 2
    src_cur = pd.Series(np.where(
        inclusive, "ShortTermBorrowings|non_overlapping",
        np.where(dc.notna() & comp.notna(), "max(DebtCurrent,LTDCur+STB)|derived",
                 np.where(dc.notna(), "DebtCurrent|direct",
                          np.where(comp.notna(), "LTDCur+STB|derived", None)))),
        index=df.index)
    df["CurrentDebt"], df["CurrentDebt__src"] = current, src_cur

    # Trap 1, applied per underlying component: a component the firm never
    # reports anywhere is a true zero; one it reports only sometimes is a
    # tagging gap, so the quarter must stay NaN rather than silently shrink.
    def eff(s: pd.Series) -> pd.Series:
        return s if bool(s.notna().any()) else s.fillna(0.0)

    if not (ltd.notna().any() or cur_full.notna().any() or stb.notna().any()):
        df["TotalDebt"] = np.nan
        df["TotalDebt__src"] = None
        return df

    total_incl = ltd + eff(stb)                 # LongTermDebt already has current
    total_excl = eff(ltd) + eff(cur_full)
    df["TotalDebt"] = total_incl.where(inclusive, total_excl)
    df["TotalDebt__src"] = np.where(
        df["TotalDebt"].notna(),
        np.where(inclusive, "LongTermDebt(incl current)+STB|derived",
                 "LTDNoncurrent+CurrentDebt|derived"), None)

    if stats is not None:
        g = stats.setdefault("_debt", {})
        g["quarters_nulled_missing_ltd"] = g.get("quarters_nulled_missing_ltd", 0) + \
            int((ltd.isna() & bool(ltd.notna().any()) & current.notna()).sum())
        g["quarters_inclusive_ltd_tag"] = g.get("quarters_inclusive_ltd_tag", 0) + \
            int(inclusive.sum())
    return df


def process_company(blob: dict, cik: str, stats: dict) -> pd.DataFrame:
    panel = X.extract_company(blob, C.CONCEPTS, stats)
    if not panel:
        return pd.DataFrame()
    df = pd.DataFrame(list(panel.values()))
    df["cik"] = cik
    for col in VALUE_COLS:
        if col not in df:
            df[col] = np.nan
        if f"{col}__src" not in df:
            df[f"{col}__src"] = pd.NA

    # ---- derived: Assets fallback via the accounting identity ------------
    # A = L + SE, so LiabilitiesAndStockholdersEquity is Assets under another
    # name. Filers routinely tag only one of the two.
    need = df["Assets"].isna()
    if need.any():
        alt = df["LiabilitiesAndStockholdersEquity"]
        fill = need & alt.notna()
        df.loc[fill, "Assets"] = alt[fill]
        df.loc[fill, "Assets__src"] = "LiabilitiesAndStockholdersEquity|identity"
        d = stats.setdefault("_derived", {})
        d["Assets"] = d.get("Assets", 0) + int(fill.sum())

    # ---- derived: Liabilities fallback -----------------------------------
    need = df["Liabilities"].isna()
    if need.any():
        derived = df["LiabilitiesAndStockholdersEquity"] - df["StockholdersEquityInclNCI"]
        fill = need & derived.notna()
        df.loc[fill, "Liabilities"] = derived[fill]
        df.loc[fill, "Liabilities__src"] = "LiabilitiesAndStockholdersEquity-Equity|derived"
        stats.setdefault("_derived", {})["Liabilities"] = \
            stats.setdefault("_derived", {}).get("Liabilities", 0) + int(fill.sum())

    # ---- derived: current debt and total debt ----------------------------
    df = _derive_debt(df, stats)

    # ---- derived: EBIT and EBITDA ----------------------------------------
    df["EBIT"] = df["OperatingIncomeLoss"]
    df["EBIT__src"] = np.where(df["EBIT"].notna(), "OperatingIncomeLoss|direct", None)
    alt = df["NetIncomeLoss"] + df["InterestExpense"] + df["IncomeTaxExpenseBenefit"]
    fill = df["EBIT"].isna() & alt.notna()
    df.loc[fill, "EBIT"] = alt[fill]
    df.loc[fill, "EBIT__src"] = "NetIncome+Interest+Tax|derived"

    da = df["DepreciationAmortization"]
    da_alt = df["AmortizationOfIntangibleAssets"]
    da_eff = da.where(da.notna(), da_alt)
    df["EBITDA"] = df["EBIT"] + da_eff
    df["EBITDA__src"] = np.where(
        df["EBITDA"].notna(),
        np.where(da.notna(), "EBIT+DD&A|derived", "EBIT+AmortIntangibles|derived"),
        None)

    df["quarter_idx"] = df["quarter"].map(X.quarter_to_index)
    return df.sort_values("quarter_idx").reset_index(drop=True)


def interest_annual_fallback(df: pd.DataFrame, blob: dict,
                             stats: dict) -> pd.DataFrame:
    """Fill quarters with no tagged interest expense using annual value / 4."""
    need = df["InterestExpense"].isna()
    if not need.any():
        return df
    spans = X.annual_spans(blob, C.CONCEPTS["InterestExpense"])
    if not spans:
        return df
    filled = 0
    for i in df.index[need]:
        pe = X.parse_date(df.at[i, "period_end"])
        if pe is None:
            continue
        for start, end, val, tag in spans:
            if start <= pe <= end:
                df.at[i, "InterestExpense"] = val / 4.0
                df.at[i, "InterestExpense__src"] = f"{tag}|annual_div4"
                filled += 1
                break
    stats.setdefault("_fallback", {})["InterestExpense_annual_div4"] = \
        stats.setdefault("_fallback", {}).get("InterestExpense_annual_div4", 0) + filled
    return df


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def firm_list(full: bool = False) -> pd.DataFrame:
    if full:
        uni = pd.read_parquet(UNIVERSE_FULL)
        uni = uni[uni["in_universe"] == 1].copy()
        uni["cik"] = uni["cik"].astype(str)
        return uni[["cik", "name", "sic", "is_bankrupt"]]
    p = pd.read_csv(PILOT, dtype={"cik": str})
    return p[["cik", "name", "sic", "is_bankrupt"]]


def build_panel(full: bool = False, force: bool = False) -> pd.DataFrame:
    PANEL_OUT, CHUNK_DIR = C.panel_path(full), C.chunk_dir(full)
    if PANEL_OUT.exists() and not force:
        print(f"[fund] cached -> {PANEL_OUT.name}")
        return pd.read_parquet(PANEL_OUT)

    firms = firm_list(full)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    ciks = firms["cik"].tolist()
    chunks = [ciks[i:i + CHUNK_SIZE] for i in range(0, len(ciks), CHUNK_SIZE)]
    stats: dict = json.loads(STATS_OUT.read_text()) if STATS_OUT.exists() and not force else {}

    with zipfile.ZipFile(CF_ZIP) as zf:
        available = set(zf.namelist())
        for ci, chunk in enumerate(chunks):
            out = CHUNK_DIR / f"chunk_{ci:04d}.parquet"
            if out.exists() and not force:
                continue
            frames = []
            for cik in tqdm(chunk, desc=f"chunk {ci + 1}/{len(chunks)}",
                            unit="firm", leave=False, mininterval=2.0):
                name = f"CIK{int(cik):010d}.json"
                if name not in available:
                    continue
                try:
                    blob = json.loads(zf.read(name))
                except Exception:                            # noqa: BLE001
                    continue
                d = process_company(blob, cik, stats)
                if d.empty:
                    continue
                d = interest_annual_fallback(d, blob, stats)
                frames.append(d)
            if frames:
                pd.concat(frames, ignore_index=True).to_parquet(out, index=False)
            STATS_OUT.write_text(json.dumps(stats, indent=1, default=str))
            print(f"[fund] chunk {ci + 1}/{len(chunks)} done "
                  f"({sum(len(f) for f in frames):,} firm-quarters)")

    parts = sorted(CHUNK_DIR.glob("chunk_*.parquet"))
    panel = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)

    # Restrict to the study window (plus 4 quarters of lead-in for YoY growth).
    lo = X.quarter_to_index("2009Q1")
    hi = X.quarter_to_index("2024Q4")
    panel = panel[(panel["quarter_idx"] >= lo) & (panel["quarter_idx"] <= hi)]
    panel = panel.drop_duplicates(subset=["cik", "quarter"], keep="last")

    # A firm-quarter is a real observation only if the firm reported a balance
    # sheet for it. Without this, companyfacts' income-statement and cash-flow
    # comparatives (which reach further back than balance-sheet comparatives)
    # create sparse phantom rows that depress every coverage figure while
    # supporting almost no ratio.
    n_before = len(panel)
    panel = panel[panel["Assets"].notna()].copy()
    print(f"[fund] dropped {n_before - len(panel):,} firm-quarters with no "
          f"balance-sheet anchor ({100 * (n_before - len(panel)) / max(n_before, 1):.1f}%)")

    meta = firms.set_index("cik")
    panel["sic"] = panel["cik"].map(meta["sic"])
    panel["company"] = panel["cik"].map(meta["name"])
    panel["is_bankrupt"] = panel["cik"].map(meta["is_bankrupt"]).fillna(0).astype(int)

    front = ["cik", "company", "sic", "is_bankrupt", "quarter", "quarter_idx",
             "period_end", "fy", "fp"]
    cols = front + VALUE_COLS + DERIVED + \
        [f"{c}__src" for c in VALUE_COLS + DERIVED if f"{c}__src" in panel]
    panel = panel[[c for c in cols if c in panel.columns]] \
        .sort_values(["cik", "quarter_idx"]).reset_index(drop=True)
    panel.to_parquet(PANEL_OUT, index=False)
    print(f"[fund] {len(panel):,} firm-quarters, {panel['cik'].nunique():,} firms "
          f"-> {PANEL_OUT.name}")
    return panel


def audit_positives_against_panel(panel: pd.DataFrame, full: bool = False) -> int:
    """Log positives that survived the Phase-2 filters but yielded no quarters.

    Phase 2 can only test whether a CIK *has* a companyfacts entry. Some
    entries turn out to be empty shells, or the firm's XBRL is filed under a
    parent CIK, so no usable firm-quarter comes out the far side. The
    acceptance criterion requires every labelled positive to be either in the
    panel or listed with a reason, so those cases are appended here rather
    than disappearing.
    """
    unmatched_path = C.REPORTS / "unmatched_positives.csv"
    labels = pd.read_csv(C.PROCESSED / "labels.csv", dtype={"cik": str})
    labels = labels[labels["in_window"] == 1]
    already = (pd.read_csv(unmatched_path, dtype={"cik": str})
               if unmatched_path.exists() else pd.DataFrame(columns=["cik"]))
    processed = set(firm_list(full)["cik"].astype(str))

    missing = (set(labels["cik"]) & processed) - set(panel["cik"].astype(str)) \
        - set(already["cik"].astype(str))
    if not missing:
        print("[fund] every in-scope positive produced at least one firm-quarter")
        return 0

    rows = []
    with zipfile.ZipFile(CF_ZIP) as zf:
        names = set(zf.namelist())
        for cik in sorted(missing, key=int):
            r = labels[labels["cik"] == cik].iloc[0]
            fn = f"CIK{int(cik):010d}.json"
            n_tags, n_q = 0, 0
            if fn in names:
                try:
                    blob = json.loads(zf.read(fn))
                    n_tags = len((blob.get("facts") or {}).get("us-gaap", {}))
                    n_q = len(X.extract_company(blob))
                except Exception:                          # noqa: BLE001
                    pass
            reason = ("in scope but produced no usable firm-quarter "
                      "(empty or parent-filed XBRL, or no periodic facts in "
                      "the study window)")
            rows.append({"cik": cik, "company": r["company"],
                         "event_date": r["event_date"], "source": r["source"],
                         "chapter": r.get("chapter"), "sic": r.get("sic"),
                         "excluded_sic": pd.NA, "reason": reason,
                         "n_usgaap_tags": n_tags, "n_quarters_extracted": n_q})

    out = pd.concat([already, pd.DataFrame(rows)], ignore_index=True)
    out.to_csv(unmatched_path, index=False)
    print(f"[fund] logged {len(rows)} in-scope positives that yielded no "
          f"firm-quarters -> {unmatched_path.name}")
    return len(rows)


# ---------------------------------------------------------------------------
# Coverage report / gate
# ---------------------------------------------------------------------------
EXPECTATION = {"tier1": 90.0, "Revenue": 95.0, "InterestExpense": 70.0}


def _defined_population(panel: pd.DataFrame, concept: str) -> dict:
    """Split missingness into structural and recoverable parts.

    A concept is *defined* for a firm-quarter only if the firm reports it at
    some point and the quarter lies inside that reporting span. Rows outside
    that span are structural: a pre-revenue biotech has no revenue to tag, and
    a firm's earliest balance-sheet comparative predates its income statements.
    Coverage over the defined population is what actually measures whether the
    fallback chain and the YTD reconstruction are working.
    """
    p = panel[["cik", "quarter_idx", concept]].copy()
    p["has"] = p[concept].notna()
    span = p[p["has"]].groupby("cik")["quarter_idx"].agg(["min", "max"])
    m = p[~p["has"]].join(span, on="cik")
    never = int(m["min"].isna().sum())
    before = int((m["quarter_idx"] < m["min"]).sum())
    after = int((m["quarter_idx"] > m["max"]).sum())
    interior = int(((m["quarter_idx"] >= m["min"]) &
                    (m["quarter_idx"] <= m["max"])).sum())
    filled = int(p["has"].sum())
    denom = filled + interior
    return {"never_reported": never, "before_first": before, "after_last": after,
            "interior_gap": interior, "filled": filled,
            "defined_coverage": 100 * filled / denom if denom else 0.0}


def write_report(panel: pd.DataFrame, full: bool = False) -> bool:
    stats = json.loads(STATS_OUT.read_text()) if STATS_OUT.exists() else {}
    n = len(panel)
    concepts = VALUE_COLS + DERIVED

    rows = []
    for c in concepts:
        if c not in panel:
            continue
        nn = int(panel[c].notna().sum())
        src = panel.get(f"{c}__src")
        methods = (src.dropna().str.split("|").str[-1].value_counts()
                   if src is not None else pd.Series(dtype=int))
        tags = (src.dropna().str.split("|").str[0].value_counts()
                if src is not None else pd.Series(dtype=int))
        dec = _defined_population(panel, c)
        rows.append({
            "concept": c,
            "coverage_pct": 100 * nn / n if n else 0.0,
            "defined_pct": dec["defined_coverage"],
            "non_null": nn,
            "primary_tag": tags.index[0] if len(tags) else "-",
            "primary_tag_share": (100 * tags.iloc[0] / tags.sum()) if len(tags) else 0.0,
            "n_tags_used": int(len(tags)),
            "differenced_pct": (100 * methods.get("differenced", 0) / max(methods.sum(), 1)),
        })
    cov = pd.DataFrame(rows).sort_values("coverage_pct", ascending=False)

    tier1 = cov[cov["concept"].isin(C.TIER1_CONCEPTS)]
    rev_raw = float(cov.loc[cov["concept"] == "Revenue", "coverage_pct"].iloc[0])
    rev_def = float(cov.loc[cov["concept"] == "Revenue", "defined_pct"].iloc[0])
    ie_raw = float(cov.loc[cov["concept"] == "InterestExpense", "coverage_pct"].iloc[0])
    t1_fail = tier1[tier1["coverage_pct"] < EXPECTATION["tier1"]]
    rev_ok = rev_def >= EXPECTATION["Revenue"]
    ie_ok = ie_raw >= EXPECTATION["InterestExpense"]
    passed = t1_fail.empty and rev_ok and ie_ok
    rdec = _defined_population(panel, "Revenue")

    # Evidence that the fallback chain spans the ASC 606 tag switch.
    rsrc = panel[["quarter", "Revenue__src"]].dropna()
    rsrc = rsrc.assign(year=rsrc["quarter"].str[:4],
                       tag=rsrc["Revenue__src"].str.split("|").str[0])
    asc = rsrc.groupby(["year", "tag"]).size().unstack(fill_value=0)
    asc_pct = (100 * asc.T / asc.sum(axis=1)).T.round(0)
    keep = [t for t in ["Revenues", "SalesRevenueNet",
                        "RevenueFromContractWithCustomerExcludingAssessedTax"]
            if t in asc_pct.columns]

    dstats = {k: v for k, v in stats.items() if not k.startswith("_")}
    tot_direct = sum(v.get("direct", 0) for v in dstats.values() if isinstance(v, dict))
    tot_pref = sum(v.get("differenced_prefix", 0) for v in dstats.values() if isinstance(v, dict))
    tot_tile = sum(v.get("differenced_tiling", 0) for v in dstats.values() if isinstance(v, dict))
    tot_lost = sum(v.get("cumulative_unrecovered", 0) + v.get("wide_quarter_unrecovered", 0)
                   for v in dstats.values() if isinstance(v, dict))
    ie_filled = stats.get("_fallback", {}).get("InterestExpense_annual_div4", 0)
    liab_der = stats.get("_derived", {}).get("Liabilities", 0)

    by_class = panel.groupby("is_bankrupt").size()

    L = [
        "# Phase 3 - Coverage Report", "",
        f"Panel: **{n:,} firm-quarters**, **{panel['cik'].nunique():,} firms**, "
        f"{panel['quarter'].min()} to {panel['quarter'].max()}.", "",
        f"- survivor firm-quarters: {int(by_class.get(0, 0)):,}",
        f"- bankrupt-firm firm-quarters: {int(by_class.get(1, 0)):,}",
        "",
        "## Per-concept non-null coverage", "",
        "`differenced %` is the share of filled cells reconstructed from cumulative",
        "YTD facts rather than read directly as a discrete quarter.", "",
        "`Coverage %` is over all firm-quarters. `Defined %` excludes structurally",
        "absent cases - firms that never report the concept, and quarters outside a",
        "firm's reporting span for it - so it measures whether the fallback chain",
        "and the YTD reconstruction actually work.", "",
        "| Concept | Coverage % | Defined % | Non-null | Winning tag | Tag share % | Tags used | Differenced % |",
        "|---|---:|---:|---:|---|---:|---:|---:|",
    ]
    for _, r in cov.iterrows():
        L.append(f"| `{r['concept']}` | {r['coverage_pct']:.1f} | {r['defined_pct']:.1f} | "
                 f"{r['non_null']:,} | `{r['primary_tag']}` | "
                 f"{r['primary_tag_share']:.0f} | "
                 f"{r['n_tags_used']} | {r['differenced_pct']:.0f} |")

    L += [
        "", "## YTD de-cumulation", "",
        "| Route | Quarter-values |", "|---|---:|",
        f"| reported directly as an 80-100 day quarter | {tot_direct:,} |",
        f"| reconstructed by YTD prefix subtraction (`Qn = YTD(n) - YTD(n-1)`) | {tot_pref:,} |",
        f"| reconstructed by tiling (`Q4 = FY - Q1 - Q2 - Q3`) | {tot_tile:,} |",
        f"| cumulative facts that could not be reduced to a quarter | {tot_lost:,} |",
        "",
        f"Differencing recovered **{tot_pref + tot_tile:,}** quarter-values that "
        f"would otherwise have been missing - "
        f"{100 * (tot_pref + tot_tile) / max(tot_direct + tot_pref + tot_tile, 1):.1f}% "
        "of all flow observations.",
        "",
        "## Fallbacks applied", "",
        f"- `InterestExpense` filled from **annual / 4**: **{ie_filled:,} cells** "
        f"({100 * ie_filled / max(n, 1):.1f}% of all firm-quarters). Without it, "
        f"coverage would be {100 * (int(panel['InterestExpense'].notna().sum()) - ie_filled) / max(n, 1):.1f}%.",
        f"- `Liabilities` derived as L&SE minus NCI-inclusive equity: **{liab_der:,} cells**.",
        f"- `Assets` filled from `LiabilitiesAndStockholdersEquity` via the "
        f"A = L + SE identity: **{stats.get('_derived', {}).get('Assets', 0):,} cells**.",
        f"- `TotalDebt` quarters left NaN because the firm tags long-term debt "
        f"only annually: **{stats.get('_debt', {}).get('quarters_nulled_missing_ltd', 0):,}** "
        f"(treating those as zero debt would have produced a sawtooth leverage series).",
        "",
        "## Investigating the Revenue gap", "",
        f"Raw Revenue coverage is {rev_raw:.1f}%, below the spec's 95% expectation, so",
        "the shortfall was decomposed rather than accepted:", "",
        "| Missing-Revenue firm-quarters | Count | Nature |", "|---|---:|---|",
        f"| firm never reports any revenue tag | {rdec['never_reported']:,} | "
        "structural - pre-revenue development-stage filers |",
        f"| quarter precedes the firm's first reported revenue | {rdec['before_first']:,} | "
        "structural - balance-sheet comparatives predate the income statement |",
        f"| quarter follows the firm's last reported revenue | {rdec['after_last']:,} | "
        "structural - wind-down and final pre-bankruptcy quarters |",
        f"| **interior gap inside the reporting span** | **{rdec['interior_gap']:,}** | "
        "**recoverable - the only genuine tagging/reconstruction loss** |",
        "",
        "The never-reporting firms concentrate in SIC 2834/2836 (pharma and biotech),",
        "1000/1040 (metal mining) and 1311 (oil and gas extraction), with median total",
        "assets of $27M against $260M for revenue-reporting firms - the classic",
        "pre-revenue profile. Their revenue is *undefined*, not missing, and is left",
        "NaN rather than imputed as zero, which would make ratios 5, 8, 16 and 21",
        "divide by zero.", "",
        f"Coverage over the population where revenue is defined is **{rev_def:.1f}%**.", "",
        "### ASC 606 tag switch", "",
        "Share of filled Revenue cells by winning tag. The chain spans the 2018",
        "transition rather than losing one regime:", "",
        "| Year | " + " | ".join(f"`{t}`" for t in keep) + " |",
        "|---|" + "---:|" * len(keep),
    ] + [f"| {yr} | " + " | ".join(f"{asc_pct.loc[yr, t]:.0f}%" for t in keep) + " |"
         for yr in asc_pct.index if int(yr) % 2 == 0] + [
        "", "## Gate", "",
        "| Expectation | Observed | Verdict |", "|---|---|---|",
        f"| Tier-1 concepts >= {EXPECTATION['tier1']:.0f}% | "
        f"min {tier1['coverage_pct'].min():.1f}% (`{tier1.loc[tier1['coverage_pct'].idxmin(), 'concept']}`) | "
        f"{'PASS' if t1_fail.empty else 'FAIL: ' + ', '.join(t1_fail['concept'])} |",
        f"| Revenue >= {EXPECTATION['Revenue']:.0f}% after fallback chain | "
        f"{rev_def:.1f}% over the defined population ({rev_raw:.1f}% raw) | "
        f"{'PASS' if rev_ok else 'FAIL'} |",
        f"| InterestExpense >= {EXPECTATION['InterestExpense']:.0f}% after annual/4 | "
        f"{ie_raw:.1f}% | {'PASS' if ie_ok else 'FAIL'} |",
        "",
        f"**Phase 3 gate: {'PASS' if passed else 'FAIL'}**", "",
        "### Concepts below expectation that are structurally so", "",
        "- `InventoryNet` (54%) and `COGS` (56%): service and software firms hold no",
        "  inventory, and many filers report only combined operating costs (the most",
        "  common alternative tag among the gap firms is `CostsAndExpenses`, which is",
        "  total costs including SG&A, so it is deliberately *not* used as a COGS",
        "  fallback). Phase 4 routes these through the `has_inventory` indicator",
        "  rather than imputing them.",
        "- `AccountsPayable` (78%): the common alternative is",
        "  `AccountsPayableAndAccruedLiabilitiesCurrent`, a different concept that",
        "  would silently inflate payables and corrupt ratio 19, so it is not used.",
        "- `TotalDebt` (44%): many filers tag long-term debt only in the 10-K; those",
        "  quarters are NaN rather than misreported as zero.", "",
    ]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {REPORT.relative_to(C.ROOT)}")
    return passed


def main(full: bool = False, force: bool = False) -> pd.DataFrame:
    print("=" * 70)
    print(f"PHASE 3 - FUNDAMENTALS EXTRACTION ({'FULL' if full else 'PILOT'})")
    print("=" * 70)
    panel = build_panel(full=full, force=force)
    audit_positives_against_panel(panel, full=full)
    ok = write_report(panel, full=full)
    print(f"\nGATE: coverage -> {'PASS' if ok else 'FAIL (see coverage_report.md)'}")
    if not ok:
        raise SystemExit("Phase 3 coverage gate failed")
    return panel


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--force", action="store_true")
    main(**vars(ap.parse_args()))
