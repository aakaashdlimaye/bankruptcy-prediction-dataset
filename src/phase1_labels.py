"""Phase 1 - Bankruptcy labels.

Three independent sources, merged on CIK then fuzzy name:

  A. EDGAR full-text search (efts.sec.gov) for 8-K Item 1.03, swept year by
     year 2009-2025. EFTS returns a structured ``items`` array per hit, so we
     filter on the actual reported item rather than on text matching.
  B. EDGAR bulk ``submissions.zip`` - every company's filing history carries an
     ``items`` field for 8-Ks. This is the authoritative, non-paginated version
     of the same signal and catches what the full-text index misses.
     (ADDED source, documented in docs/DECISIONS.md.)
  C. Florida-UCLA-LoPucki BRD Cases table (large public bankruptcies, ends
     Dec 2022) - cross-check plus chapter and date enrichment.

Dates from different sources are reconciled **within an event**, not across a
firm's whole history: a firm can go bankrupt more than once (PG&E 2001 and
2019; Trump Entertainment four times), so raw dates are clustered with a
365-day linkage and only dates inside one cluster are treated as the same
event. The firm's headline ``event_date`` is the first event falling inside the
study window.

Outputs
-------
data/processed/labels.csv         one row per bankrupt firm
data/processed/labels_events.csv  one row per (firm, distinct bankruptcy event)
reports/labels_report.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from rapidfuzz import fuzz, process

import config as C
import sec_client as sec

EFTS_RAW = C.INTERIM / "efts_8k_item103.csv"
SUBS_RAW = C.INTERIM / "submissions_8k_item103.csv"
LOPUCKI_RAW = C.INTERIM / "lopucki_parsed.csv"
LABELS_OUT = C.PROCESSED / "labels.csv"
EVENTS_OUT = C.PROCESSED / "labels_events.csv"
REVIEW_OUT = C.REPORTS / "labels_fuzzy_review.csv"
UNMATCHED_LOP_OUT = C.REPORTS / "lopucki_unmatched.csv"
REPORT_OUT = C.REPORTS / "labels_report.md"

# Only genuine legal-form suffixes are stripped. Descriptive words
# (communications, holdings, group, systems, ...) carry identity: stripping
# them collapses "Frontier Communications Corp" and "Frontier Holdings Inc"
# onto the same key and produces false 100-score matches.
SUFFIX_RE = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|llc|l l c|"
    r"lp|llp|plc|nv|n v|sa|s a|ag|gmbh|the)\b", re.I)
NONALNUM_RE = re.compile(r"[^a-z0-9 ]+")
WS_RE = re.compile(r"\s+")

EVENT_LINKAGE_DAYS = 365      # dates closer than this belong to one bankruptcy
FUZZY_ACCEPT = 90
FUZZY_REVIEW = 80


def norm_name(name: str) -> str:
    """Normalise a company name for fuzzy matching."""
    if not isinstance(name, str):
        return ""
    s = name.lower()
    s = re.sub(r"\(cik\s*\d+\)", " ", s)
    s = re.sub(r"\([^)]*\)", " ", s)          # trailing "(2003)", "(AAPL)"
    s = NONALNUM_RE.sub(" ", s)
    s = SUFFIX_RE.sub(" ", s)
    return WS_RE.sub(" ", s).strip()


def _cik(v) -> str:
    """Normalise a CIK to its unpadded decimal string; '' when absent."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    s = s.split(".")[0].lstrip("0")
    return s if s.isdigit() else ""


# ---------------------------------------------------------------------------
# Source A - EDGAR full-text search
# ---------------------------------------------------------------------------
def sweep_efts(years: list[int], force: bool = False) -> pd.DataFrame:
    if EFTS_RAW.exists() and not force:
        print(f"[efts] cached -> {EFTS_RAW.name}")
        return pd.read_csv(EFTS_RAW, dtype={"cik": str})

    rows: list[dict] = []
    for year in years:
        pending = [(f"{year}-01-01", f"{year}-12-31")]
        n = 0
        while pending:
            start, end = pending.pop(0)
            got, total = _efts_window(start, end, rows)
            if total > 9000 and start.endswith("01-01") and end.endswith("12-31"):
                print(f"[efts] {year}: {total} hits > window cap, splitting by quarter")
                rows[:] = [r for r in rows if not (start <= r["file_date"] <= end)]
                pending = [(f"{year}-{a}", f"{year}-{b}") for a, b in
                           [("01-01", "03-31"), ("04-01", "06-30"),
                            ("07-01", "09-30"), ("10-01", "12-31")]]
                n = 0
                continue
            n += got
        print(f"[efts] {year}: {n} item-1.03 document hits")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("EFTS sweep returned nothing - check network/endpoint")
    df.to_csv(EFTS_RAW, index=False)
    print(f"[efts] wrote {len(df)} rows -> {EFTS_RAW.name}")
    return df


def _efts_window(start: str, end: str, rows: list[dict]) -> tuple[int, int]:
    frm, page, got, total = 0, 100, 0, 0
    while True:
        params = {"q": '"Item 1.03"', "forms": "8-K", "dateRange": "custom",
                  "startdt": start, "enddt": end, "from": frm}
        data = sec.get_json(C.EFTS_URL, params=params,
                            cache_key=f"efts_{start}_{end}_{frm}")
        total = data["hits"]["total"]["value"]
        hits = data["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            src = h["_source"]
            if "1.03" not in (src.get("items") or []):
                continue          # mentions the phrase but does not report the item
            ciks = src.get("ciks") or []
            names = src.get("display_names") or []
            sics = src.get("sics") or []
            for i, cik in enumerate(ciks):
                rows.append({
                    "cik": _cik(cik),
                    "company": re.sub(r"\s*\(CIK\s*\d+\)\s*$", "",
                                      names[i] if i < len(names)
                                      else (names[0] if names else "")).strip(),
                    "file_date": src.get("file_date"),
                    "form": src.get("form"),
                    "accession": src.get("adsh"),
                    "sic": sics[i] if i < len(sics) else (sics[0] if sics else None),
                    "items": ",".join(src.get("items") or []),
                    "is_primary_filer": int(i == 0),
                })
                got += 1
        frm += page
        if frm >= min(total, 9900):
            break
    return got, total


# ---------------------------------------------------------------------------
# Source B - bulk submissions
# ---------------------------------------------------------------------------
def sweep_submissions(force: bool = False) -> pd.DataFrame:
    import scan_submissions

    if not SUBS_RAW.exists() or force:
        if not (C.RAW / "submissions.zip").exists():
            print("[subs] submissions.zip missing - skipping source B")
            return pd.DataFrame(columns=["cik", "company", "file_date", "form",
                                         "accession", "sic", "items",
                                         "is_primary_filer"])
        scan_submissions.main(force=force)
    df = pd.read_csv(SUBS_RAW, dtype={"cik": str})
    print(f"[subs] {len(df):,} item-1.03 filings, {df['cik'].nunique():,} CIKs")
    return df


# ---------------------------------------------------------------------------
# Source C - LoPucki BRD
# ---------------------------------------------------------------------------
def load_lopucki(force: bool = False) -> pd.DataFrame:
    if LOPUCKI_RAW.exists() and not force:
        return pd.read_csv(LOPUCKI_RAW, dtype={"cik": str})
    candidates = sorted(C.RAW.glob("lopucki_cases*.csv"))
    if not candidates:
        print("!! LoPucki Cases table not found in data/raw/.")
        print("!! Download it from https://lopucki.law.ufl.edu ('Download cases "
              "table'), save as data/raw/lopucki_cases.csv and re-run phase 1.")
        return pd.DataFrame(columns=["cik", "company", "event_date", "chapter", "sic"])

    path = candidates[0]
    raw = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            raw = pd.read_csv(path, low_memory=False, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise RuntimeError(f"could not decode {path}")

    df = pd.DataFrame({
        "company": raw["NameCorp"].astype(str).str.strip(),
        "cik": raw["CikBefore"].map(_cik),
        "event_date": pd.to_datetime(raw["DateFiled"], format="mixed",
                                     errors="coerce"),
        "chapter": raw["Chapter"].astype(str).str.strip(),
        "sic": raw["SICPrimary"],
    })
    df = df[df["event_date"].notna()].copy()
    df["event_date"] = df["event_date"].dt.strftime("%Y-%m-%d")
    df.to_csv(LOPUCKI_RAW, index=False)
    print(f"[lopucki] parsed {len(df)} cases -> {LOPUCKI_RAW.name}")
    return df


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def _edgar_events(efts: pd.DataFrame, subs: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for df, src in ((efts, "8K_FTS"), (subs, "8K_SUBMISSIONS")):
        if df is None or df.empty:
            continue
        d = df.copy()
        d["cik"] = d["cik"].map(_cik)
        d["date"] = pd.to_datetime(d["file_date"], errors="coerce")
        d = d[(d["cik"] != "") & d["date"].notna()]
        d["source"] = src
        d["chapter"] = pd.NA
        if "is_primary_filer" not in d:
            d["is_primary_filer"] = 1
        frames.append(d[["cik", "company", "date", "sic", "source", "chapter",
                         "is_primary_filer"]])
    return (pd.concat(frames, ignore_index=True) if frames
            else pd.DataFrame(columns=["cik", "company", "date", "sic",
                                       "source", "chapter", "is_primary_filer"]))


def _attach_lopucki(lop: pd.DataFrame, edgar: pd.DataFrame,
                    stats: dict) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    """Give every LoPucki case a CIK: its own, else a fuzzy name match."""
    review, unmatched, rows = [], [], []
    if lop.empty:
        return pd.DataFrame(columns=edgar.columns), review, unmatched

    names = (edgar.sort_values("date")
             .drop_duplicates("cik", keep="last")[["cik", "company"]]
             .reset_index(drop=True))
    names["norm"] = names["company"].map(norm_name)
    choices = names["norm"].tolist()
    edgar_ciks = set(names["cik"])

    n_cik = n_fuzzy = 0
    for _, r in lop.iterrows():
        cik, method = _cik(r["cik"]), "lopucki_cik"
        if cik:
            n_cik += 1 if cik in edgar_ciks else 0
        else:
            key = norm_name(r["company"])
            hit = process.extractOne(key, choices, scorer=fuzz.token_sort_ratio,
                                     score_cutoff=FUZZY_REVIEW) if key else None
            if hit is None:
                unmatched.append({"lopucki_name": r["company"],
                                  "lopucki_date": r["event_date"],
                                  "chapter": r["chapter"],
                                  "reason": "no name candidate >= 80"})
                continue
            cand, score, idx = hit
            if score < FUZZY_ACCEPT:
                review.append({"lopucki_name": r["company"],
                               "lopucki_date": r["event_date"],
                               "candidate_edgar_name": names.at[idx, "company"],
                               "candidate_cik": names.at[idx, "cik"],
                               "score": round(score, 1)})
                unmatched.append({"lopucki_name": r["company"],
                                  "lopucki_date": r["event_date"],
                                  "chapter": r["chapter"],
                                  "reason": f"fuzzy {score:.0f} in 80-90 review band"})
                continue
            cik, method = names.at[idx, "cik"], f"fuzzy_{int(score)}"
            n_fuzzy += 1
        rows.append({"cik": cik, "company": r["company"],
                     "date": pd.to_datetime(r["event_date"]), "sic": r["sic"],
                     "source": "LOPUCKI", "chapter": r["chapter"],
                     "is_primary_filer": 1, "match_method": method})

    stats["lopucki_cases"] = int(len(lop))
    stats["lopucki_with_own_cik"] = int((lop["cik"].map(_cik) != "").sum())
    stats["lopucki_cik_in_edgar"] = n_cik
    stats["lopucki_matched_fuzzy"] = n_fuzzy
    stats["lopucki_review_80_90"] = len(review)
    stats["lopucki_unmatched"] = len(unmatched)
    return pd.DataFrame(rows), review, unmatched


def _cluster_events(dates: list[pd.Timestamp]) -> list[list[int]]:
    """Single-linkage clustering of sorted dates with a 365-day threshold."""
    order = sorted(range(len(dates)), key=lambda i: dates[i])
    clusters: list[list[int]] = []
    for i in order:
        if clusters and (dates[i] - dates[clusters[-1][-1]]).days <= EVENT_LINKAGE_DAYS:
            clusters[-1].append(i)
        else:
            clusters.append([i])
    return clusters


def merge_labels(efts: pd.DataFrame, subs: pd.DataFrame,
                 lop: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    stats: dict = {}
    stats["efts_filings"] = int(efts["accession"].nunique()) if not efts.empty else 0
    stats["efts_ciks"] = int(efts["cik"].map(_cik).nunique()) if not efts.empty else 0
    stats["subs_filings"] = int(subs["accession"].nunique()) if not subs.empty else 0
    stats["subs_ciks"] = int(subs["cik"].map(_cik).nunique()) if not subs.empty else 0

    edgar = _edgar_events(efts, subs)
    if edgar.empty:
        raise RuntimeError("no EDGAR-derived bankruptcy events")
    lop_ev, review, unmatched = _attach_lopucki(lop, edgar, stats)

    allev = pd.concat([edgar, lop_ev], ignore_index=True)
    allev["cik"] = allev["cik"].map(_cik)
    allev = allev[allev["cik"] != ""]

    # ---- cluster each firm's dates into distinct bankruptcy events --------
    ev_rows: list[dict] = []
    for cik, g in allev.groupby("cik", sort=False):
        g = g.reset_index(drop=True)
        dates = list(g["date"])
        for ci, idxs in enumerate(_cluster_events(dates), start=1):
            sub = g.loc[idxs]
            srcs = sorted(set(sub["source"]))
            dmin, dmax = sub["date"].min(), sub["date"].max()
            chapters = [c for c in sub["chapter"].dropna().unique()
                        if str(c) not in ("nan", "<NA>", "")]
            edgar_d = sub.loc[sub["source"] != "LOPUCKI", "date"]
            lop_d = sub.loc[sub["source"] == "LOPUCKI", "date"]
            ev_rows.append({
                "cik": cik,
                "company": sub["company"].iloc[0],
                "event_seq": ci,
                # spec rule: with two sources for one event, keep the earlier date
                "event_date": dmin,
                "edgar_date": edgar_d.min() if len(edgar_d) else pd.NaT,
                "lopucki_date": lop_d.min() if len(lop_d) else pd.NaT,
                "date_discrepancy_days": (
                    int((edgar_d.min() - lop_d.min()).days)
                    if len(edgar_d) and len(lop_d) else pd.NA),
                "intra_event_spread_days": int((dmax - dmin).days),
                "source": "+".join(srcs),
                "chapter": chapters[0] if chapters else pd.NA,
                "sic": sub["sic"].dropna().iloc[0] if sub["sic"].notna().any() else pd.NA,
                "is_primary_filer": int(sub["is_primary_filer"].max()),
                "n_filings": int(len(sub)),
            })
    events = pd.DataFrame(ev_rows).sort_values(["cik", "event_date"])

    both = events["edgar_date"].notna() & events["lopucki_date"].notna()
    stats["events_total"] = int(len(events))
    stats["events_both_sources"] = int(both.sum())
    if both.any():
        d = events.loc[both, "date_discrepancy_days"].astype(float)
        stats["date_disagree_gt7d"] = int((d.abs() > 7).sum())
        stats["median_date_gap_days"] = float(d.median())

    # ---- collapse to one row per firm ------------------------------------
    firm_rows: list[dict] = []
    for cik, g in events.groupby("cik", sort=False):
        g = g.sort_values("event_date").reset_index(drop=True)
        inwin = g[(g["event_date"] >= C.STUDY_START) &
                  (g["event_date"] <= C.STUDY_END)]
        chosen = inwin.iloc[0] if len(inwin) else g.iloc[0]
        prior = g[g["event_date"] < chosen["event_date"]]
        firm_rows.append({
            "cik": cik,
            "company": chosen["company"],
            "event_date": chosen["event_date"],
            "prior_event_date": prior["event_date"].max() if len(prior) else pd.NaT,
            "n_events": int(len(g)),
            "all_event_dates": ";".join(g["event_date"].dt.strftime("%Y-%m-%d")),
            "source": chosen["source"],
            "chapter": chosen["chapter"],
            "sic": chosen["sic"],
            "is_primary_filer": int(chosen["is_primary_filer"]),
            "date_discrepancy_days": chosen["date_discrepancy_days"],
            "in_window": int(C.STUDY_START <= chosen["event_date"].strftime("%Y-%m-%d")
                             <= C.STUDY_END),
        })
    firms = pd.DataFrame(firm_rows).sort_values("event_date").reset_index(drop=True)

    if review:
        pd.DataFrame(review).sort_values("score", ascending=False) \
            .to_csv(REVIEW_OUT, index=False)
    if unmatched:
        pd.DataFrame(unmatched).to_csv(UNMATCHED_LOP_OUT, index=False)

    return firms, events, stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _universe_size() -> tuple[int, str]:
    meta_path = C.INTERIM / "company_meta.parquet"
    if not meta_path.exists():
        return 7000, "assumed ~7,000-firm universe (company_meta.parquet absent)"
    m = pd.read_parquet(meta_path, columns=["sic", "has_periodic_in_window"])
    per = m[m["has_periodic_in_window"] == 1]
    nonfin = per[per["sic"].isna() | (per["sic"] < C.SIC_EXCLUDE_LO) |
                 (per["sic"] > C.SIC_EXCLUDE_HI)]
    return int(len(nonfin)), ("distinct non-financial CIKs with a 10-K/10-Q "
                              "period end inside 2010-2024, from submissions.zip")


def write_report(firms: pd.DataFrame, events: pd.DataFrame, stats: dict) -> None:
    inwin = firms[firms["in_window"] == 1]
    per_year = inwin.groupby(inwin["event_date"].dt.year).size()
    per_src = firms["source"].value_counts()
    uni, uni_note = _universe_size()
    rate = 100 * len(inwin) / uni
    ev_in = events[(events["event_date"] >= C.STUDY_START) &
                   (events["event_date"] <= C.STUDY_END)]

    L = [
        "# Phase 1 - Bankruptcy Labels Report", "",
        "One row per bankrupt **firm** in `data/processed/labels.csv`; one row per",
        "distinct bankruptcy **event** in `data/processed/labels_events.csv`.", "",
        "## Source counts", "",
        "| Source | Distinct filings/cases | Distinct CIKs |", "|---|---:|---:|",
        f"| A. EDGAR full-text search, 8-K item 1.03 | {stats.get('efts_filings', 0):,} | {stats.get('efts_ciks', 0):,} |",
        f"| B. EDGAR bulk submissions, 8-K item 1.03 | {stats.get('subs_filings', 0):,} | {stats.get('subs_ciks', 0):,} |",
        f"| C. LoPucki BRD cases (all years, 1980-2022) | {stats.get('lopucki_cases', 0):,} | {stats.get('lopucki_with_own_cik', 0):,} carry a CIK |",
        "",
        "## Cross-source overlap", "",
        f"- LoPucki cases carrying a CIK that also appears in the EDGAR 8-K set: **{stats.get('lopucki_cik_in_edgar', 0)}**",
        f"- LoPucki cases with no CIK, matched by **fuzzy name >= {FUZZY_ACCEPT}**: **{stats.get('lopucki_matched_fuzzy', 0)}**",
        f"- LoPucki cases in the **{FUZZY_REVIEW}-{FUZZY_ACCEPT} manual-review** band: {stats.get('lopucki_review_80_90', 0)} "
        f"(`reports/labels_fuzzy_review.csv`)",
        f"- LoPucki cases left unmatched: {stats.get('lopucki_unmatched', 0)} "
        f"(`reports/lopucki_unmatched.csv`) - overwhelmingly pre-2001 filings, "
        f"before EDGAR carried 8-K item tags at all",
        "",
        "### Date reconciliation", "",
        "Raw dates are clustered per firm with a 365-day single linkage, so a firm",
        "that filed twice (PG&E 2001 and 2019; Trump Entertainment four times) keeps",
        "two distinct events instead of collapsing to its earliest. Within one",
        "event, the **earlier** of the EDGAR and LoPucki dates is kept, per spec.", "",
        f"- Distinct bankruptcy events identified: **{stats.get('events_total', 0):,}**",
        f"- Events observed by both EDGAR and LoPucki: {stats.get('events_both_sources', 0):,}",
        f"- ... where the two dates differ by more than 7 days: {stats.get('date_disagree_gt7d', 0):,} "
        f"(median signed gap {stats.get('median_date_gap_days', float('nan')):.1f} days, EDGAR minus LoPucki)",
        "",
        "## Firms by source combination", "",
        "| Source combination | Firms |", "|---|---:|",
    ] + [f"| {k} | {v:,} |" for k, v in per_src.items()] + [
        "", "## Event-date distribution (firms with event in 2010-2024)", "",
        "| Year | Bankrupt firms |", "|---:|---:|",
    ] + [f"| {int(y)} | {int(n):,} |" for y, n in per_year.items()] + [
        f"| **Total** | **{len(inwin):,}** |", "",
        "## Headline numbers", "",
        f"- Distinct bankrupt firms, all years, any source: **{len(firms):,}**",
        f"- Distinct bankrupt firms with event date inside 2010-2024: **{len(inwin):,}**",
        f"- Distinct bankruptcy *events* inside 2010-2024: **{len(ev_in):,}** "
        f"(some firms filed more than once)",
        f"- Firms with more than one distinct event: {int((firms['n_events'] > 1).sum()):,}",
        f"- Firms whose headline event is a co-registrant subsidiary filing only: "
        f"{int((firms['is_primary_filer'] == 0).sum()):,}",
        "",
        "### Implied positive rate", "",
        f"- Denominator used: **{uni:,}** ({uni_note})",
        f"- Positive rate: **{rate:.2f}%**",
        "",
        "The spec's 2-4% sanity target assumes a universe of large, continuously",
        "listed firms. This raw rate is higher because the label sweep also catches",
        "micro-cap and shell filers that never produce eight usable quarters of XBRL",
        "fundamentals. The rate that matters for the model is measured after the",
        "universe and sequence filters, and is reported in",
        "`reports/DATASET_REPORT.md`.", "",
        "## Gate", "",
        f"Required: >= 250 distinct bankrupt firms with event dates inside 2010-2024. "
        f"Observed **{len(inwin):,}** -> **{'PASS' if len(inwin) >= 250 else 'FAIL'}**.",
        "",
    ]
    REPORT_OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] -> {REPORT_OUT.relative_to(C.ROOT)}")


def main(skip_submissions: bool = False, force: bool = False) -> pd.DataFrame:
    print("=" * 70)
    print("PHASE 1 - BANKRUPTCY LABELS")
    print("=" * 70)
    efts = sweep_efts(C.LABEL_SWEEP_YEARS, force=force)
    subs = pd.DataFrame() if skip_submissions else sweep_submissions(force=force)
    lop = load_lopucki(force=force)

    firms, events, stats = merge_labels(efts, subs, lop)
    firms.to_csv(LABELS_OUT, index=False)
    events.to_csv(EVENTS_OUT, index=False)
    print(f"[labels] {len(firms):,} firms -> {LABELS_OUT.relative_to(C.ROOT)}")
    print(f"[labels] {len(events):,} events -> {EVENTS_OUT.relative_to(C.ROOT)}")

    write_report(firms, events, stats)
    n = int(firms["in_window"].sum())
    print(f"\nGATE: {n} bankrupt firms with event in 2010-2024 "
          f"(need >= 250) -> {'PASS' if n >= 250 else 'FAIL'}")
    if n < 250:
        raise SystemExit("Phase 1 gate failed")
    return firms


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-submissions", action="store_true")
    ap.add_argument("--force", action="store_true")
    main(**vars(ap.parse_args()))
