"""Unit tests for Phase 5: horizon labelling, the dropout trap, windowing, splits."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
import pytest

import config as C
import phase5_sequences as P5
from xbrl_extract import quarter_to_index


def panel(cik: str, quarters: list[str], value: float = 1.0,
          missing: set[str] | None = None) -> pd.DataFrame:
    missing = missing or set()
    rows = []
    for q in quarters:
        row = {"cik": cik, "company": "TEST", "is_bankrupt": 0,
               "quarter": q, "quarter_idx": quarter_to_index(q),
               "period_end": pd.Timestamp(_qend(q)),
               "has_inventory": 1, "has_debt": 1}
        for f in C.RATIO_NAMES:
            row[f] = np.nan if q in missing else value
        rows.append(row)
    return pd.DataFrame(rows)


def _qend(q: str) -> str:
    y, i = int(q[:4]), int(q[-1])
    return {1: f"{y}-03-31", 2: f"{y}-06-30", 3: f"{y}-09-30", 4: f"{y}-12-31"}[i]


def labels(cik: str, event: str) -> pd.DataFrame:
    return pd.DataFrame([{"cik": cik, "event_date": event, "in_window": 1}])


# ---------------------------------------------------------------------------
# Labelling
# ---------------------------------------------------------------------------
def test_horizon_labels_count_quarters_forward_from_period_end():
    qs = [f"2018Q{i}" for i in (1, 2, 3, 4)] + [f"2019Q{i}" for i in (1, 2)]
    p, _ = P5.label_firm_quarters(panel("1", qs), labels("1", "2019-08-15"))
    got = {r["quarter"]: (r["y1"], r["y2"], r["y3"], r["y4"])
           for _, r in p.iterrows()}
    assert got["2019Q2"] == (1, 1, 1, 1)      # event ~1 quarter after 30 Jun
    assert got["2019Q1"] == (0, 1, 1, 1)      # ~2 quarters
    assert got["2018Q4"] == (0, 0, 1, 1)      # ~3 quarters
    assert got["2018Q3"] == (0, 0, 0, 1)      # ~4 quarters
    assert got["2018Q2"] == (0, 0, 0, 0)      # beyond the horizon


def test_post_petition_quarters_are_excluded_entirely():
    qs = ["2019Q1", "2019Q2", "2019Q3", "2019Q4"]
    p, _ = P5.label_firm_quarters(panel("1", qs), labels("1", "2019-08-15"))
    assert set(p["quarter"]) == {"2019Q1", "2019Q2"}


def test_survivors_get_all_zero_labels():
    p, _ = P5.label_firm_quarters(panel("1", ["2018Q1", "2018Q2"]),
                                  pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    assert (p[["y1", "y2", "y3", "y4"]].to_numpy() == 0).all()
    assert p["is_positive_firm"].eq(0).all()


def test_dropout_trap_window_ends_at_last_filing_not_the_event():
    """A firm that stops filing three quarters early is still a labelled positive."""
    qs = [f"2017Q{i}" for i in (1, 2, 3, 4)] + [f"2018Q{i}" for i in (1, 2, 3, 4)]
    p, dropout = P5.label_firm_quarters(panel("1", qs), labels("1", "2019-08-15"))
    assert len(p) == 8                          # nothing dropped: all pre-event
    last = p.loc[p["quarter"] == "2018Q4"].iloc[0]
    assert (last["y1"], last["y2"], last["y3"], last["y4"]) == (0, 0, 1, 1)
    assert int(dropout.iloc[0]["gap_quarters"]) == 3


# ---------------------------------------------------------------------------
# Forward fill
# ---------------------------------------------------------------------------
def test_forward_fill_is_capped_at_two_quarters():
    qs = ["2016Q1", "2016Q2", "2017Q2"]          # 3-quarter hole after 2016Q2
    g = P5.prepare_firm(panel("1", qs, value=5.0))
    by_q = dict(zip(g["quarter_idx"], g[C.RATIO_NAMES[0]]))
    assert by_q[quarter_to_index("2016Q3")] == 5.0     # gap of 1 - filled
    assert by_q[quarter_to_index("2016Q4")] == 5.0     # gap of 2 - filled
    assert pd.isna(by_q[quarter_to_index("2017Q1")])   # gap of 3 - not filled


def test_missing_quarters_are_materialised_and_flagged_unobserved():
    g = P5.prepare_firm(panel("1", ["2016Q1", "2016Q3"]))
    assert len(g) == 3
    assert list(g["was_observed"]) == [1, 0, 1]


# ---------------------------------------------------------------------------
# Windowing and splits
# ---------------------------------------------------------------------------
def _full_history(cik: str, start: str, n: int) -> list[str]:
    i0 = quarter_to_index(start)
    from xbrl_extract import index_to_quarter
    return [index_to_quarter(i0 + k) for k in range(n)]


def test_window_shape_and_stride():
    qs = _full_history("1", "2015Q1", 12)
    p, _ = P5.label_firm_quarters(panel("1", qs),
                                  pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    Xa, Ma, Ya, Ia, man = P5.build_windows(p)
    assert Xa.shape == (12 - C.WINDOW_LEN + 1, C.WINDOW_LEN, len(C.RATIO_NAMES))
    assert Ya.shape[1] == len(C.HORIZONS)
    assert Ia.shape == (Xa.shape[0], C.WINDOW_LEN, 2)
    assert list(man["end_quarter"])[:2] == ["2016Q4", "2017Q1"]


def test_window_rejected_when_completeness_rule_fails():
    qs = _full_history("1", "2015Q1", 8)
    # 5 of 8 quarters null for every feature -> mean non-null 3 < 6
    p = panel("1", qs, missing=set(qs[:5]))
    p, _ = P5.label_firm_quarters(p, pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    *_, man = P5.build_windows(p)
    assert man.empty


def test_window_kept_when_completeness_rule_passes():
    qs = _full_history("1", "2015Q1", 8)
    p = panel("1", qs, missing={qs[0], qs[1]})     # 6 of 8 non-null
    p, _ = P5.label_firm_quarters(p, pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    *_, man = P5.build_windows(p)
    assert len(man) == 1


def test_split_is_a_function_of_the_end_quarter_only():
    assert P5.split_of(quarter_to_index("2019Q4")) == "train"
    assert P5.split_of(quarter_to_index("2020Q1")) == "val"
    assert P5.split_of(quarter_to_index("2021Q4")) == "val"
    assert P5.split_of(quarter_to_index("2022Q1")) == "test"
    assert P5.split_of(quarter_to_index("2024Q4")) == "test"
    assert P5.split_of(quarter_to_index("2025Q1")) is None


def test_straddling_window_belongs_to_the_split_of_its_end_quarter():
    qs = _full_history("1", "2018Q2", 8)          # 2018Q2..2020Q1
    p, _ = P5.label_firm_quarters(panel("1", qs),
                                  pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    *_, man = P5.build_windows(p)
    assert len(man) == 1
    assert man.iloc[0]["end_quarter"] == "2020Q1"
    assert man.iloc[0]["split"] == "val"          # despite starting in the train era


def test_no_window_index_appears_in_two_splits():
    qs = _full_history("1", "2017Q1", 32)
    p, _ = P5.label_firm_quarters(panel("1", qs),
                                  pd.DataFrame(columns=["cik", "event_date", "in_window"]))
    *_, man = P5.build_windows(p)
    key = man["cik"] + "|" + man["end_quarter"]
    assert man.assign(k=key).groupby("k")["split"].nunique().max() == 1


# ---------------------------------------------------------------------------
# Scaler
# ---------------------------------------------------------------------------
def test_scaler_standardises_and_imputes_missing_to_zero():
    Xtr = np.random.RandomState(0).normal(5.0, 2.0,
                                          size=(200, C.WINDOW_LEN, len(C.RATIO_NAMES)))
    sc = P5.fit_scaler(Xtr)
    Z = P5.apply_scaler(Xtr, sc)
    assert abs(float(Z.reshape(-1, len(C.RATIO_NAMES))[:, 0].mean())) < 0.05
    assert abs(float(Z.reshape(-1, len(C.RATIO_NAMES))[:, 0].std()) - 1.0) < 0.05

    Xn = Xtr.copy()
    Xn[0, 0, 0] = np.nan
    assert P5.apply_scaler(Xn, sc)[0, 0, 0] == 0.0      # imputed to the train mean


def test_scaler_never_sees_validation_data():
    """Fitting on train only must ignore an extreme value living in val."""
    Xtr = np.ones((50, C.WINDOW_LEN, len(C.RATIO_NAMES)))
    sc_train = P5.fit_scaler(Xtr)
    Xall = np.concatenate([Xtr, np.full((50, C.WINDOW_LEN, len(C.RATIO_NAMES)), 1e6)])
    sc_all = P5.fit_scaler(Xall)
    assert sc_train["mean"][0] == pytest.approx(1.0)
    assert sc_all["mean"][0] > 1.0                     # contaminated, for contrast
