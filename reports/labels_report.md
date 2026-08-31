# Phase 1 - Bankruptcy Labels Report

One row per bankrupt **firm** in `data/processed/labels.csv`; one row per
distinct bankruptcy **event** in `data/processed/labels_events.csv`.

## Source counts

| Source | Distinct filings/cases | Distinct CIKs |
|---|---:|---:|
| A. EDGAR full-text search, 8-K item 1.03 | 2,269 | 1,258 |
| B. EDGAR bulk submissions, 8-K item 1.03 | 3,614 | 2,000 |
| C. LoPucki BRD cases (all years, 1980-2022) | 1,218 | 992 carry a CIK |

## Cross-source overlap

- LoPucki cases carrying a CIK that also appears in the EDGAR 8-K set: **506**
- LoPucki cases with no CIK, matched by **fuzzy name >= 90**: **5**
- LoPucki cases in the **80-90 manual-review** band: 32 (`reports/labels_fuzzy_review.csv`)
- LoPucki cases left unmatched: 221 (`reports/lopucki_unmatched.csv`) - overwhelmingly pre-2001 filings, before EDGAR carried 8-K item tags at all

### Date reconciliation

Raw dates are clustered per firm with a 365-day single linkage, so a firm
that filed twice (PG&E 2001 and 2019; Trump Entertainment four times) keeps
two distinct events instead of collapsing to its earliest. Within one
event, the **earlier** of the EDGAR and LoPucki dates is kept, per spec.

- Distinct bankruptcy events identified: **2,736**
- Events observed by both EDGAR and LoPucki: 451
- ... where the two dates differ by more than 7 days: 40 (median signed gap 1.0 days, EDGAR minus LoPucki)

## Firms by source combination

| Source combination | Firms |
|---|---:|
| 8K_FTS+8K_SUBMISSIONS | 906 |
| 8K_SUBMISSIONS | 663 |
| LOPUCKI | 506 |
| 8K_FTS+8K_SUBMISSIONS+LOPUCKI | 329 |
| 8K_SUBMISSIONS+LOPUCKI | 69 |

## Event-date distribution (firms with event in 2010-2024)

| Year | Bankrupt firms |
|---:|---:|
| 2010 | 127 |
| 2011 | 97 |
| 2012 | 72 |
| 2013 | 76 |
| 2014 | 49 |
| 2015 | 63 |
| 2016 | 105 |
| 2017 | 63 |
| 2018 | 51 |
| 2019 | 61 |
| 2020 | 91 |
| 2021 | 20 |
| 2022 | 28 |
| 2023 | 82 |
| 2024 | 81 |
| **Total** | **1,066** |

## Headline numbers

- Distinct bankrupt firms, all years, any source: **2,473**
- Distinct bankrupt firms with event date inside 2010-2024: **1,066**
- Distinct bankruptcy *events* inside 2010-2024: **1,161** (some firms filed more than once)
- Firms with more than one distinct event: 243
- Firms whose headline event is a co-registrant subsidiary filing only: 0

### Implied positive rate

- Denominator used: **11,962** (distinct non-financial CIKs with a 10-K/10-Q period end inside 2010-2024, from submissions.zip)
- Positive rate: **8.91%**

The spec's 2-4% sanity target assumes a universe of large, continuously
listed firms. This raw rate is higher because the label sweep also catches
micro-cap and shell filers that never produce eight usable quarters of XBRL
fundamentals. The rate that matters for the model is measured after the
universe and sequence filters, and is reported in
`reports/DATASET_REPORT.md`.

## Gate

Required: >= 250 distinct bankrupt firms with event dates inside 2010-2024. Observed **1,066** -> **PASS**.
