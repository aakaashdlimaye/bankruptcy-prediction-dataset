"""Unit tests for Phase 4: ratio arithmetic, structural rules, winsorisation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import pytest

import config as C
from phase4_ratios import (apply_structural_rules, compute_ratios, safe_div,
                           structural_indicators, winsorise)

CONCEPT_COLS = list(C.CONCEPTS) + ["TotalDebt", "CurrentDebt", "EBIT", "EBITDA"]


def make_panel(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in CONCEPT_COLS:
        if c not in df:
            df[c] = np.nan
    if "quarter_idx" not in df:
        df["quarter_idx"] = range(len(df))
    if "cik" not in df:
        df["cik"] = "1"
    if "period_end" not in df:
        df["period_end"] = pd.date_range("2015-03-31", periods=len(df), freq="QE")
    return df


BASE = dict(Assets=1000.0, AssetsCurrent=400.0, LiabilitiesCurrent=200.0,
            Liabilities=600.0, StockholdersEquity=400.0, CashAndEquivalents=50.0,
            InventoryNet=100.0, AccountsReceivable=80.0, AccountsPayable=40.0,
            RetainedEarnings=-150.0, LongTermDebtNoncurrent=300.0,
            Revenue=500.0, COGS=300.0, NetIncomeLoss=25.0, EBIT=60.0,
            EBITDA=90.0, InterestExpense=10.0, TotalDebt=350.0, OCF=45.0,
            CapEx=15.0)


def test_all_28_ratios_match_hand_arithmetic():
    r = compute_ratios(make_panel([BASE])).iloc[0]
    assert r["r01_current_ratio"] == pytest.approx(400 / 200)
    assert r["r02_quick_ratio"] == pytest.approx((400 - 100) / 200)
    assert r["r03_cash_ratio"] == pytest.approx(50 / 200)
    assert r["r04_wc_to_ta"] == pytest.approx((400 - 200) / 1000)
    assert r["r05_net_profit_margin"] == pytest.approx(25 / 500)
    assert r["r06_roa"] == pytest.approx(25 / 1000)
    assert r["r07_roe"] == pytest.approx(25 / 400)
    assert r["r08_ebitda_margin"] == pytest.approx(90 / 500)
    assert r["r09_ebit_to_ta"] == pytest.approx(60 / 1000)
    assert r["r10_re_to_ta"] == pytest.approx(-150 / 1000)
    assert r["r11_debt_to_equity"] == pytest.approx(350 / 400)
    assert r["r12_debt_to_assets"] == pytest.approx(350 / 1000)
    assert r["r13_interest_coverage"] == pytest.approx(60 / 10)
    assert r["r14_equity_to_liabilities"] == pytest.approx(400 / 600)
    assert r["r15_ltd_to_ta"] == pytest.approx(300 / 1000)
    assert r["r16_asset_turnover"] == pytest.approx(500 / 1000)
    assert r["r17_inventory_turnover"] == pytest.approx(300 / 100)
    assert r["r18_receivables_turnover"] == pytest.approx(500 / 80)
    assert r["r19_payables_turnover"] == pytest.approx(300 / 40)
    q = 365.0 / 4
    assert r["r20_cash_conversion_cycle"] == pytest.approx(
        q * 100 / 300 + q * 80 / 500 - q * 40 / 300)
    assert r["r25_ocf_to_cl"] == pytest.approx(45 / 200)
    assert r["r26_fcf_to_ta"] == pytest.approx((45 - 15) / 1000)
    assert r["r27_accrual_quality"] == pytest.approx(45 / 25)
    assert r["r28_ocf_to_debt"] == pytest.approx(45 / 350)
    assert r["r29_negative_equity_flag"] == 0.0


def test_total_debt_is_not_total_liabilities():
    """Ratios 11/12/15/28 must use interest-bearing debt, never total liabilities."""
    r = compute_ratios(make_panel([BASE])).iloc[0]
    assert r["r12_debt_to_assets"] == pytest.approx(0.35)      # 350/1000, not 600/1000
    assert r["r14_equity_to_liabilities"] == pytest.approx(400 / 600)   # this one does


def test_negative_equity_flag_and_ratios_kept():
    p = make_panel([{**BASE, "StockholdersEquity": -200.0}])
    r = compute_ratios(p).iloc[0]
    assert r["r29_negative_equity_flag"] == 1.0
    assert r["r07_roe"] == pytest.approx(25 / -200)     # computed, not dropped
    assert r["r11_debt_to_equity"] == pytest.approx(350 / -200)


def test_retained_earnings_negative_is_preserved():
    r = compute_ratios(make_panel([BASE])).iloc[0]
    assert r["r10_re_to_ta"] < 0


def test_zero_denominator_yields_nan_not_inf():
    p = make_panel([{**BASE, "LiabilitiesCurrent": 0.0, "Revenue": 0.0}])
    r = compute_ratios(p).iloc[0]
    # Zero *denominator* -> undefined.
    for col in ("r01_current_ratio", "r03_cash_ratio", "r05_net_profit_margin",
                "r25_ocf_to_cl"):
        assert pd.isna(r[col]), col
    # Zero *numerator* over a good denominator is a real zero, not undefined.
    assert r["r16_asset_turnover"] == pytest.approx(0.0)


def test_negative_or_zero_interest_expense_gives_nan_coverage():
    for ie in (0.0, -5.0):
        r = compute_ratios(make_panel([{**BASE, "InterestExpense": ie}])).iloc[0]
        assert pd.isna(r["r13_interest_coverage"])


def test_safe_div_handles_inf():
    out = safe_div(pd.Series([1.0, 1.0]), pd.Series([0.0, 2.0]))
    assert pd.isna(out.iloc[0]) and out.iloc[1] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Growth ratios: t vs t-4, matched on quarter index
# ---------------------------------------------------------------------------
def test_growth_uses_t_minus_4_not_previous_row():
    rows = []
    for i, rev in enumerate([100, 110, 120, 130, 200]):
        rows.append({**BASE, "Revenue": float(rev), "quarter_idx": 8000 + i})
    r = compute_ratios(make_panel(rows))
    assert pd.isna(r["r21_revenue_growth"].iloc[3])          # no t-4 yet
    assert r["r21_revenue_growth"].iloc[4] == pytest.approx((200 - 100) / 100)


def test_growth_requires_both_quarters_and_respects_gaps():
    """A missing quarter must not let t-1 masquerade as t-4."""
    rows = [{**BASE, "Revenue": 100.0, "quarter_idx": 8000},
            {**BASE, "Revenue": 500.0, "quarter_idx": 8005}]   # gap: 8004 absent
    r = compute_ratios(make_panel(rows))
    assert pd.isna(r["r21_revenue_growth"].iloc[1])


def test_growth_does_not_cross_firms():
    rows = [{**BASE, "cik": "1", "Revenue": 100.0, "quarter_idx": 8000},
            {**BASE, "cik": "2", "Revenue": 500.0, "quarter_idx": 8004}]
    r = compute_ratios(make_panel(rows))
    assert pd.isna(r["r21_revenue_growth"]).all()


def test_growth_denominator_uses_absolute_value():
    """A loss shrinking toward zero must give positive growth, not negative."""
    rows = [{**BASE, "NetIncomeLoss": -100.0, "quarter_idx": 8000},
            {**BASE, "NetIncomeLoss": -50.0, "quarter_idx": 8004}]
    r = compute_ratios(make_panel(rows))
    assert r["r22_net_income_growth"].iloc[1] == pytest.approx((-50 - -100) / 100)


# ---------------------------------------------------------------------------
# Structural indicators
# ---------------------------------------------------------------------------
def test_service_firm_has_no_inventory_and_ratios_are_undefined():
    rows = [{**BASE, "InventoryNet": np.nan, "quarter_idx": 8000 + i}
            for i in range(8)]
    p = make_panel(rows)
    ind = structural_indicators(p)
    assert ind["has_inventory"].iloc[0] == 0
    r, stats = apply_structural_rules(compute_ratios(p), p, ind)
    for col in C.INVENTORY_RATIOS:
        assert r[col].isna().all(), col
    assert stats["firms_without_inventory"] == 1


def test_firm_with_inventory_keeps_its_inventory_ratios():
    rows = [{**BASE, "quarter_idx": 8000 + i} for i in range(8)]
    p = make_panel(rows)
    ind = structural_indicators(p)
    assert ind["has_inventory"].iloc[0] == 1
    r, _ = apply_structural_rules(compute_ratios(p), p, ind)
    assert r["r17_inventory_turnover"].notna().all()


def test_debt_free_firm_has_no_interest_coverage():
    rows = [{**BASE, "TotalDebt": np.nan, "InterestExpense": np.nan,
             "quarter_idx": 8000 + i} for i in range(8)]
    p = make_panel(rows)
    ind = structural_indicators(p)
    assert ind["has_debt"].iloc[0] == 0
    r, _ = apply_structural_rules(compute_ratios(p), p, ind)
    assert r["r13_interest_coverage"].isna().all()


def test_annual_only_debt_tagger_still_counts_as_having_debt():
    """Debt tagged in one quarter of four must not read as a debt-free firm."""
    rows = [{**BASE, "TotalDebt": np.nan, "InterestExpense": np.nan,
             "quarter_idx": 8000 + i} for i in range(8)]
    rows[3]["TotalDebt"] = 500.0
    ind = structural_indicators(make_panel(rows))
    assert ind["has_debt"].iloc[0] == 1


# ---------------------------------------------------------------------------
# Winsorisation is a leakage rule
# ---------------------------------------------------------------------------
def test_winsorisation_bounds_come_only_from_the_training_period():
    n = 200
    rows = []
    for i in range(n):
        # Post-2019 rows carry an extreme value that must not move the bounds.
        pe = pd.Timestamp("2015-03-31") if i < 100 else pd.Timestamp("2022-03-31")
        rows.append({**BASE, "Assets": 1000.0,
                     "NetIncomeLoss": 25.0 if i < 100 else 1e9,
                     "period_end": pe, "quarter_idx": 8000 + i})
    p = make_panel(rows)
    raw = compute_ratios(p)
    win, meta = winsorise(raw, p)

    b = meta["bounds"]["r06_roa"]
    assert b["n_train_obs"] == 100
    assert b["p99"] == pytest.approx(0.025)          # train-only value 25/1000
    # The clip derived from train is applied to the later period too.
    assert win["r06_roa"].max() == pytest.approx(0.025)
    assert raw["r06_roa"].max() > 1000               # untouched raw copy


def test_binary_flag_is_not_winsorised():
    rows = [{**BASE, "period_end": pd.Timestamp("2015-03-31"),
             "quarter_idx": 8000 + i} for i in range(50)]
    p = make_panel(rows)
    _, meta = winsorise(compute_ratios(p), p)
    assert "r29_negative_equity_flag" not in meta["bounds"]
    assert "r29_negative_equity_flag" in meta["excluded_from_winsorisation"]


def test_ratio_name_list_is_29_and_matches_output_columns():
    r = compute_ratios(make_panel([BASE]))
    assert list(r.columns) == C.RATIO_NAMES
    assert len(C.RATIO_NAMES) == 29
