# Phase 2 - Firm Universe Report

## Funnel

| Step | Firms |
|---|---:|
| CIKs in submissions.zip | 983,019 |
| ... with a 10-K/10-Q period end in 2010-2024 | 18,035 |
| ... excluding SIC 6000-6799 (financials) | 11,962 |
| ... with an entry in companyfacts.zip | 10,758 |

## SIC resolution

| Source of SIC | Firms in scope |
|---|---:|
| submissions | 10,569 |
| unresolved (kept, flagged) | 189 |

## Positive class

- Labelled bankrupt firms with event in 2010-2024: **1,066**
- ... that survive the universe filters and can enter the panel: **789**
- ... logged in `reports/unmatched_positives.csv` instead: **277**

| Reason a positive cannot enter the panel | Firms |
|---|---:|
| SIC excluded (financial 6000-6799) | 103 |
| no 10-K/10-Q with a period end in 2010-2024 | 102 |
| no entry in companyfacts.zip (never filed XBRL) | 72 |

## Pilot universe

- Positives (all of them - never subsampled): **789**
- Survivors (random, seed=42): **789**
- Total pilot firms: **1,578**

The pilot is deliberately positive-enriched: the spec forbids subsampling
the positive class, and the identified positives alone already exceed the
~500-firm pilot budget. Class rates quoted for the pilot are therefore not
population rates; the `--full` run restores the true base rate.
