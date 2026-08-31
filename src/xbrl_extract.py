"""XBRL fact -> firm-quarter panel, including YTD de-cumulation.

This module is deliberately free of I/O so it can be unit-tested against
synthetic fixtures for both filer styles (discrete-quarter filers and
cumulative-YTD filers).

Three rules implement the spec's structural traps:

1. **Span check before differencing.** A duration fact is accepted as a
   discrete quarter only if its span is 80-100 days. Anything longer is
   treated as cumulative and reconstructed by subtracting the fact that shares
   its period start (within 7 days, to tolerate 52/53-week calendars) and ends
   exactly one quarter earlier. A filer already reporting discrete quarters has
   no same-start prefix, so it can never be double-subtracted.

2. **Instant vs duration.** Facts with no ``start`` are balance-sheet instants,
   taken at each fiscal quarter end.

3. **Deduplication.** For a given (concept, period) the fiscal-year 10-K value
   beats a 10-Q comparative; otherwise the latest filing wins.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as C

QUARTER_ENDS = ((3, 31), (6, 30), (9, 30), (12, 31))
START_TOLERANCE_DAYS = 7


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------
def parse_date(s) -> date | None:
    if isinstance(s, date):
        return s
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def quarter_label(d: date) -> str:
    """Map a period-end date to the calendar quarter whose end is nearest.

    Fiscal quarter ending 31 Jan -> prior-year Q4 (31 days away) rather than
    Q1 (59 days away). This is the standard Compustat-style alignment; it is
    documented in docs/DECISIONS.md.
    """
    best, best_gap = None, None
    for yr in (d.year - 1, d.year, d.year + 1):
        for qi, (m, dd) in enumerate(QUARTER_ENDS, start=1):
            qe = date(yr, m, dd)
            gap = abs((d - qe).days)
            if best_gap is None or gap < best_gap:
                best, best_gap = (yr, qi), gap
    return f"{best[0]}Q{best[1]}"


def quarter_end_date(q: str) -> date:
    yr, qi = int(q[:4]), int(q[-1])
    m, dd = QUARTER_ENDS[qi - 1]
    return date(yr, m, dd)


def quarter_to_index(q: str) -> int:
    """Monotone integer index so quarter arithmetic is trivial."""
    return int(q[:4]) * 4 + (int(q[-1]) - 1)


def index_to_quarter(i: int) -> str:
    return f"{i // 4}Q{i % 4 + 1}"


def quarter_add(q: str, n: int) -> str:
    return index_to_quarter(quarter_to_index(q) + n)


# ---------------------------------------------------------------------------
# Fact model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class QFact:
    quarter: str
    period_end: date
    value: float
    tag: str
    method: str          # "direct" | "differenced"
    form: str
    filed: str
    fy: int | None
    fp: str | None
    span_days: int | None


def _rank(f: dict) -> tuple:
    """Dedup priority: FY 10-K value beats 10-Q comparative; else latest filed."""
    is_fy_10k = 1 if (str(f.get("fp")) == "FY"
                      and str(f.get("form", "")).startswith("10-K")) else 0
    return (is_fy_10k, str(f.get("filed") or ""), str(f.get("accn") or ""))


def usable_facts(blob: dict, tag: str, unit: str = "USD") -> list[dict]:
    """Pull the USD facts for one us-gaap tag, filtered to periodic forms."""
    node = ((blob.get("facts") or {}).get("us-gaap") or {}).get(tag)
    if not node:
        return []
    out = []
    for f in (node.get("units") or {}).get(unit, []):
        if str(f.get("form", "")) not in C.ACCEPTED_FORMS:
            continue
        if f.get("val") is None or parse_date(f.get("end")) is None:
            continue
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# Instants
# ---------------------------------------------------------------------------
def instants_to_quarters(facts: list[dict], tag: str) -> dict[str, QFact]:
    by_end: dict[date, dict] = {}
    for f in facts:
        if f.get("start"):                       # duration fact, not an instant
            continue
        end = parse_date(f["end"])
        cur = by_end.get(end)
        if cur is None or _rank(f) > _rank(cur):
            by_end[end] = f

    out: dict[str, QFact] = {}
    for end, f in by_end.items():
        q = quarter_label(end)
        cand = QFact(q, end, float(f["val"]), tag, "direct", str(f.get("form", "")),
                     str(f.get("filed") or ""), f.get("fy"), f.get("fp"), None)
        prev = out.get(q)
        # If two balance-sheet dates land in the same calendar quarter, keep the
        # one closer to the quarter end.
        if prev is None or (abs((cand.period_end - quarter_end_date(q)).days)
                            < abs((prev.period_end - quarter_end_date(q)).days)):
            out[q] = cand
    return out


# ---------------------------------------------------------------------------
# Durations (the YTD trap)
# ---------------------------------------------------------------------------
def _dedup_durations(facts: list[dict]) -> list[dict]:
    by_period: dict[tuple[date, date], dict] = {}
    for f in facts:
        start, end = parse_date(f.get("start")), parse_date(f.get("end"))
        if start is None or end is None or end <= start:
            continue
        key = (start, end)
        cur = by_period.get(key)
        if cur is None or _rank(f) > _rank(cur):
            by_period[key] = f
    return [{**f, "_start": k[0], "_end": k[1],
             "_span": (k[1] - k[0]).days + 1} for k, f in by_period.items()]


def durations_to_quarters(facts: list[dict], tag: str,
                          stats: dict | None = None) -> dict[str, QFact]:
    """Return discrete quarterly values, differencing YTD ladders where needed.

    Two reconstruction routes, tried in order, so both filer styles work:

    * **Prefix** - subtract the same-fiscal-year cumulative fact ending exactly
      one quarter earlier (``Q3 = YTD(Q3) - YTD(Q2)``, ``Q4 = FY - YTD(Q3)``).
      This is the YTD-filer case named in the spec.
    * **Tiling** - subtract a contiguous run of already-known discrete quarters
      that exactly covers the cumulative period except its final quarter
      (``Q4 = FY - Q1 - Q2 - Q3``). This is the discrete-quarter filer, whose
      10-K still reports only an annual total and who has no cumulative prefix.

    Neither route can double-subtract: a fact already inside the 80-100 day
    quarter band is taken as-is and never differenced, and the tiling route
    verifies the subtracted quarters butt up against each other and against
    the period start before it accepts them.
    """
    rows = _dedup_durations([f for f in facts if f.get("start")])
    if not rows:
        return {}
    lo, hi = C.QUARTER_SPAN
    rows.sort(key=lambda r: (r["_start"], r["_end"]))

    def bump(key: str) -> None:
        if stats is not None:
            stats[key] = stats.get(key, 0) + 1

    # --- pass A: facts already reported as discrete quarters ---------------
    candidates: list[QFact] = []
    known: list[dict] = []          # {"start","end","val"} accepted quarters
    cumulative: list[dict] = []
    for r in rows:
        span = r["_span"]
        if lo <= span <= hi:
            candidates.append(QFact(
                quarter_label(r["_end"]), r["_end"], float(r["val"]), tag,
                "direct", str(r.get("form", "")), str(r.get("filed") or ""),
                r.get("fy"), r.get("fp"), span))
            known.append({"start": r["_start"], "end": r["_end"],
                          "val": float(r["val"])})
            bump("direct")
        elif span < lo:
            bump("too_short")
        else:
            cumulative.append(r)

    # --- pass B: reconstruct quarters from cumulative facts ----------------
    # Shortest span first so YTD(Q2) resolves before FY needs it.
    for r in sorted(cumulative, key=lambda x: x["_span"]):
        derived = _from_prefix(r, rows, lo, hi)
        method_stat = "differenced_prefix"
        if derived is None:
            derived = _from_tiling(r, known, lo, hi)
            method_stat = "differenced_tiling"
        if derived is None:
            bump("wide_quarter_unrecovered" if hi < r["_span"] <= 120
                 else "cumulative_unrecovered")
            continue
        val, qstart = derived
        candidates.append(QFact(
            quarter_label(r["_end"]), r["_end"], val, tag, "differenced",
            str(r.get("form", "")), str(r.get("filed") or ""),
            r.get("fy"), r.get("fp"), (r["_end"] - qstart).days + 1))
        known.append({"start": qstart, "end": r["_end"], "val": val})
        bump(method_stat)

    out: dict[str, QFact] = {}
    for c in candidates:
        prev = out.get(c.quarter)
        if prev is None or _cand_rank(c) > _cand_rank(prev):
            out[c.quarter] = c
    return out


def _from_prefix(r: dict, rows: list[dict], lo: int, hi: int):
    """Q_n = YTD(n) - YTD(n-1), both sharing a fiscal-year start."""
    best = None
    for p in rows:
        if p is r or p["_end"] >= r["_end"]:
            continue
        if abs((p["_start"] - r["_start"]).days) > START_TOLERANCE_DAYS:
            continue
        if lo <= (r["_end"] - p["_end"]).days <= hi:
            if best is None or p["_end"] > best["_end"]:
                best = p
    if best is None:
        return None
    return float(r["val"]) - float(best["val"]), best["_end"] + timedelta(days=1)


def _from_tiling(r: dict, known: list[dict], lo: int, hi: int):
    """Q_n = cumulative - (contiguous run of known quarters covering the rest)."""
    inside = sorted(
        (k for k in known
         if k["start"] >= r["_start"] - timedelta(days=START_TOLERANCE_DAYS)
         and k["end"] < r["_end"]),
        key=lambda k: k["start"])
    if not inside:
        return None
    if abs((inside[0]["start"] - r["_start"]).days) > START_TOLERANCE_DAYS:
        return None

    total, cursor = 0.0, None
    for k in inside:
        if cursor is not None and abs((k["start"] - cursor).days) > START_TOLERANCE_DAYS + 1:
            return None                      # gap in the run - cannot tile
        total += k["val"]
        cursor = k["end"] + timedelta(days=1)
        tail = (r["_end"] - k["end"]).days
        if lo <= tail <= hi:
            return float(r["val"]) - total, k["end"] + timedelta(days=1)
    return None


def _cand_rank(c: QFact) -> tuple:
    """A directly-reported quarter beats a reconstructed one; else latest filed."""
    return (1 if c.method == "direct" else 0, c.filed)


# ---------------------------------------------------------------------------
# Concept-level assembly
# ---------------------------------------------------------------------------
def extract_concept(blob: dict, concept: str, spec: dict,
                    stats: dict | None = None) -> dict[str, QFact]:
    """Walk the fallback chain; first tag that supplies a quarter wins."""
    result: dict[str, QFact] = {}
    for tag in spec["tags"]:
        facts = usable_facts(blob, tag)
        if not facts:
            continue
        tstats = None if stats is None else stats.setdefault(concept, {})
        got = (instants_to_quarters(facts, tag) if spec["kind"] == "instant"
               else durations_to_quarters(facts, tag, tstats))
        for q, qf in got.items():
            if q not in result:
                result[q] = qf
    return result


def annual_spans(blob: dict, spec: dict) -> list[tuple[date, date, float, str]]:
    """Annual (~365-day) duration facts, for the interest-expense /4 fallback.

    Returns (start, end, value, tag) with the fiscal-year 10-K value preferred
    over any 10-Q restatement of the same period.
    """
    lo, hi = C.ANNUAL_SPAN
    best: dict[tuple[date, date], tuple[tuple, float, str]] = {}
    for tag in spec["tags"]:
        for f in usable_facts(blob, tag):
            start, end = parse_date(f.get("start")), parse_date(f.get("end"))
            if start is None or end is None:
                continue
            span = (end - start).days + 1
            if not (lo <= span <= hi):
                continue
            key = (start, end)
            r = _rank(f)
            if key not in best or r > best[key][0]:
                best[key] = (r, float(f["val"]), tag)
    return [(k[0], k[1], v[1], v[2]) for k, v in best.items()]


def extract_company(blob: dict, concepts: dict | None = None,
                    stats: dict | None = None) -> dict[str, dict]:
    """Return {quarter: {concept: value, concept__src: 'tag|method', ...}}."""
    concepts = concepts or C.CONCEPTS
    panel: dict[str, dict] = {}
    for name, spec in concepts.items():
        for q, qf in extract_concept(blob, name, spec, stats).items():
            row = panel.setdefault(q, {"quarter": q})
            row[name] = qf.value
            row[f"{name}__src"] = f"{qf.tag}|{qf.method}"
            # Period metadata comes from whichever instant anchors the quarter.
            if spec["kind"] == "instant" and ("period_end" not in row or
                                              name == "Assets"):
                row["period_end"] = qf.period_end.isoformat()
                row["fy"] = qf.fy
                row["fp"] = qf.fp
            row.setdefault("period_end", qf.period_end.isoformat())
            row.setdefault("fy", qf.fy)
            row.setdefault("fp", qf.fp)
    return panel
