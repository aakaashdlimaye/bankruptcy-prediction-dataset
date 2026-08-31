# Phase 5 - Sequences Report

## The dropout trap

Bankrupt firms stop filing before the petition date, so the look-back
window ends at the last available filing. Distribution of
(event date - last available filing) for positives that reach the panel:

| Quarters between last filing and event | Firms |
|---:|---:|
| 1 | 393 |
| 2 | 221 |
| 3 | 65 |
| 4 | 22 |
| 5 | 22 |
| 6 | 10 |
| 7 | 10 |
| 8 | 4 |
| 9+ | 18 |

Median gap: **1.0 quarters** (90 days); mean 2.12. 372 of 765 positives (49%) stop filing at least two quarters ahead - anchoring windows to the
bankruptcy date instead of the last filing would have discarded them.

## Completeness rule

A window of 8 quarters is kept when, **averaged over the 29 features**, at least 6 of the 8 quarters are non-null:

```
mean_over_features( count_of_non_null_quarters(feature) ) >= 6
```

Two further conditions:

- gaps are forward-filled within a firm for at most 2 quarters before windowing, and never across an event date (post-petition rows are removed first, so no fill can cross one);
- the window's **end quarter must be a real filing**, never a
  forward-filled placeholder, because that quarter carries the label.

## Window counts

| Split | Window end quarters | Windows | Firms | Positive windows (y4) | Positive rate |
|---|---|---:|---:|---:|---:|
| train | <= 2019Q4 | 12,634 | 813 | 986 | 7.80% |
| val | 2020Q1-2021Q4 | 2,357 | 375 | 108 | 4.58% |
| test | 2022Q1-2024Q4 | 3,009 | 370 | 363 | 12.06% |
| **all** | | **18,000** | **948** | **1,457** | **8.09%** |

## Positives per split and horizon

| Split | y1 | y2 | y3 | y4 | windows |
|---|---:|---:|---:|---:|---:|
| train | 154 | 410 | 693 | 986 | 12,634 |
| val | 37 | 71 | 92 | 108 | 2,357 |
| test | 60 | 158 | 260 | 363 | 3,009 |

## Data completeness of the retained windows

- mean share of observed (non-forward-filled) quarters per window: **7.94 of 8**
- mean share of non-null feature cells per window: **88.1%**
