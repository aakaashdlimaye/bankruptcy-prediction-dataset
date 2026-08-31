"""Unit tests for the YTD de-cumulation trap.

Both filer styles are covered with synthetic fixtures, as the spec requires:
  * Style A - cumulative year-to-date (Q1, YTD-Q2, YTD-Q3, FY)
  * Style B - discrete quarters in the 10-Qs, annual total in the 10-K
plus the mixed style (both columns present) and 52/53-week calendars.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from xbrl_extract import (durations_to_quarters, instants_to_quarters,
                          quarter_add, quarter_label, quarter_to_index)

TAG = "Revenues"


def dur(start, end, val, form="10-Q", filed="2020-05-01", fy=2020, fp="Q1"):
    return {"start": start, "end": end, "val": val, "form": form,
            "filed": filed, "fy": fy, "fp": fp, "accn": f"a{val}"}


def inst(end, val, form="10-Q", filed="2020-05-01", fy=2020, fp="Q1"):
    return {"end": end, "val": val, "form": form, "filed": filed,
            "fy": fy, "fp": fp, "accn": f"i{val}"}


# ---------------------------------------------------------------------------
# Style A - cumulative YTD filer
# ---------------------------------------------------------------------------
def test_style_a_cumulative_ytd_filer():
    """Q1 as reported; Q2/Q3 by differencing YTD; Q4 = FY - YTD(Q3)."""
    facts = [
        dur("2020-01-01", "2020-03-31", 100.0, fp="Q1"),
        dur("2020-01-01", "2020-06-30", 250.0, fp="Q2", filed="2020-08-01"),
        dur("2020-01-01", "2020-09-30", 400.0, fp="Q3", filed="2020-11-01"),
        dur("2020-01-01", "2020-12-31", 600.0, form="10-K", fp="FY",
            filed="2021-02-01"),
    ]
    q = durations_to_quarters(facts, TAG)
    assert q["2020Q1"].value == pytest.approx(100.0)
    assert q["2020Q2"].value == pytest.approx(150.0)   # 250 - 100
    assert q["2020Q3"].value == pytest.approx(150.0)   # 400 - 250
    assert q["2020Q4"].value == pytest.approx(200.0)   # 600 - 400
    assert q["2020Q1"].method == "direct"
    assert all(q[k].method == "differenced" for k in ("2020Q2", "2020Q3", "2020Q4"))
    # The four discrete quarters must sum back to the reported annual total.
    assert sum(q[k].value for k in ("2020Q1", "2020Q2", "2020Q3", "2020Q4")) \
        == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# Style B - discrete-quarter filer
# ---------------------------------------------------------------------------
def test_style_b_discrete_quarter_filer_is_not_double_subtracted():
    """Discrete quarters pass through untouched; Q4 comes from annual - Q1..Q3."""
    facts = [
        dur("2020-01-01", "2020-03-31", 100.0, fp="Q1"),
        dur("2020-04-01", "2020-06-30", 150.0, fp="Q2", filed="2020-08-01"),
        dur("2020-07-01", "2020-09-30", 150.0, fp="Q3", filed="2020-11-01"),
        dur("2020-01-01", "2020-12-31", 600.0, form="10-K", fp="FY",
            filed="2021-02-01"),
    ]
    q = durations_to_quarters(facts, TAG)
    # If these had been blindly differenced, Q2 would be 50 and Q3 would be 0.
    assert q["2020Q1"].value == pytest.approx(100.0)
    assert q["2020Q2"].value == pytest.approx(150.0)
    assert q["2020Q3"].value == pytest.approx(150.0)
    assert q["2020Q4"].value == pytest.approx(200.0)   # 600 - 400 via tiling
    for k in ("2020Q1", "2020Q2", "2020Q3"):
        assert q[k].method == "direct"
    assert q["2020Q4"].method == "differenced"


def test_style_b_without_annual_yields_three_quarters_not_four():
    facts = [
        dur("2020-01-01", "2020-03-31", 100.0),
        dur("2020-04-01", "2020-06-30", 150.0),
        dur("2020-07-01", "2020-09-30", 150.0),
    ]
    q = durations_to_quarters(facts, TAG)
    assert set(q) == {"2020Q1", "2020Q2", "2020Q3"}


# ---------------------------------------------------------------------------
# Mixed style - both the 3-month and YTD columns are tagged
# ---------------------------------------------------------------------------
def test_mixed_style_prefers_the_directly_reported_quarter():
    facts = [
        dur("2020-01-01", "2020-03-31", 100.0),
        dur("2020-04-01", "2020-06-30", 150.0, filed="2020-08-01"),   # discrete
        dur("2020-01-01", "2020-06-30", 250.0, filed="2020-08-01"),   # YTD
    ]
    q = durations_to_quarters(facts, TAG)
    assert q["2020Q2"].value == pytest.approx(150.0)
    assert q["2020Q2"].method == "direct"


# ---------------------------------------------------------------------------
# 52/53-week retail calendar
# ---------------------------------------------------------------------------
def test_52_53_week_calendar_spans_are_accepted():
    """13-week quarters and a 53-week year still de-cumulate correctly."""
    facts = [
        dur("2020-02-02", "2020-05-02", 100.0),                 # 91 days
        dur("2020-02-02", "2020-08-01", 250.0, filed="2020-09-01"),
        dur("2020-02-02", "2020-10-31", 400.0, filed="2020-12-01"),
        dur("2020-02-02", "2021-01-30", 600.0, form="10-K", fp="FY",
            filed="2021-03-15"),                                # 364 days
    ]
    q = durations_to_quarters(facts, TAG)
    vals = sorted(v.value for v in q.values())
    assert vals == pytest.approx([100.0, 150.0, 150.0, 200.0])


def test_negative_flows_difference_correctly():
    """CapEx / losses are negative or shrinking; differencing must keep sign."""
    facts = [
        dur("2020-01-01", "2020-03-31", -50.0),
        dur("2020-01-01", "2020-06-30", -120.0, filed="2020-08-01"),
        dur("2020-01-01", "2020-09-30", -100.0, filed="2020-11-01"),
    ]
    q = durations_to_quarters(facts, TAG)
    assert q["2020Q2"].value == pytest.approx(-70.0)
    assert q["2020Q3"].value == pytest.approx(20.0)


def test_six_month_only_filer_cannot_fabricate_quarters():
    """A lone 6-month fact with no Q1 must not be emitted as a quarter."""
    facts = [dur("2020-01-01", "2020-06-30", 250.0)]
    assert durations_to_quarters(facts, TAG) == {}


def test_gap_in_ytd_ladder_is_not_bridged():
    """9-month minus 3-month spans two quarters - must be rejected, not split."""
    facts = [
        dur("2020-01-01", "2020-03-31", 100.0),
        dur("2020-01-01", "2020-09-30", 400.0, filed="2020-11-01"),
    ]
    q = durations_to_quarters(facts, TAG)
    assert set(q) == {"2020Q1"}


def test_non_periodic_forms_are_ignored_upstream():
    """S-1/8-K durations never reach here; forms are filtered in usable_facts."""
    facts = [dur("2020-01-01", "2020-03-31", 100.0, form="8-K")]
    q = durations_to_quarters(facts, TAG)
    assert q["2020Q1"].value == pytest.approx(100.0)   # filtering is upstream


# ---------------------------------------------------------------------------
# Instants and dedup
# ---------------------------------------------------------------------------
def test_instant_prefers_10k_over_10q_comparative():
    facts = [
        inst("2020-12-31", 900.0, form="10-Q", fp="Q1", filed="2021-05-01"),
        inst("2020-12-31", 1000.0, form="10-K", fp="FY", filed="2021-02-15"),
    ]
    q = instants_to_quarters(facts, "Assets")
    assert q["2020Q4"].value == pytest.approx(1000.0)
    assert q["2020Q4"].form == "10-K"


def test_instant_latest_filing_wins_within_same_form_class():
    facts = [
        inst("2020-03-31", 500.0, filed="2020-05-01"),
        inst("2020-03-31", 520.0, filed="2020-11-01"),      # restated later
    ]
    q = instants_to_quarters(facts, "Assets")
    assert q["2020Q1"].value == pytest.approx(520.0)


def test_duration_dedup_prefers_fy_10k():
    facts = [
        dur("2020-01-01", "2020-12-31", 590.0, form="10-Q", fp="Q1",
            filed="2021-05-01"),
        dur("2020-01-01", "2020-12-31", 600.0, form="10-K", fp="FY",
            filed="2021-02-01"),
        dur("2020-01-01", "2020-09-30", 400.0, filed="2020-11-01"),
    ]
    q = durations_to_quarters(facts, TAG)
    assert q["2020Q4"].value == pytest.approx(200.0)    # uses the 10-K's 600


# ---------------------------------------------------------------------------
# Calendar alignment
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("d,expected", [
    (date(2019, 3, 31), "2019Q1"),
    (date(2019, 12, 31), "2019Q4"),
    (date(2019, 1, 31), "2018Q4"),     # nearest quarter end is 31 Dec
    (date(2019, 2, 28), "2019Q1"),     # nearest is 31 Mar
    (date(2020, 5, 2), "2020Q1"),      # retail Q1 ending early May
    (date(2021, 1, 30), "2020Q4"),
    (date(2019, 6, 29), "2019Q2"),
    (date(2019, 9, 28), "2019Q3"),
])
def test_quarter_label(d, expected):
    assert quarter_label(d) == expected


def test_quarter_arithmetic_round_trips():
    assert quarter_add("2019Q4", 1) == "2020Q1"
    assert quarter_add("2020Q1", -1) == "2019Q4"
    assert quarter_add("2019Q1", 4) == "2020Q1"
    assert quarter_to_index("2020Q1") - quarter_to_index("2019Q1") == 4
