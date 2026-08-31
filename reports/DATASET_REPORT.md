# Dataset Report

Bankruptcy prediction from temporal sequences of quarterly financial
ratios, US listed non-financial firms, 2010-2024. Built from SEC EDGAR
XBRL company facts plus three independent bankruptcy label sources.

Universe run: **PILOT**.

## 1. Headline counts

| Quantity | Value |
|---|---:|
| Distinct bankrupt firms identified (any year) | 2,473 |
| ... with an event date inside 2010-2024 | 1,066 |
| Distinct bankruptcy events inside 2010-2024 | 1,161 |
| Non-financial firms with 10-K/10-Q in window (full universe) | 10,758 |
| Firms in the pilot run | 1,578 |
| Firms yielding at least one usable firm-quarter | 1,565 |
| Firm-quarters in the fundamentals panel | 40,691 |
| Firm-quarters in the ratio panel | 40,691 |
| 8-quarter sequences built | 18,000 |
| Firms contributing at least one sequence | 948 |

## 2. Splits, positives and class rates

Split is assigned by the window's **end quarter**.

| Split | End quarters | Sequences | Firms | pos y1 | pos y2 | pos y3 | pos y4 | rate y1 | rate y4 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | <= 2019Q4 | 12,634 | 813 | 154 | 410 | 693 | 986 | 1.22% | 7.80% |
| val | 2020Q1-2021Q4 | 2,357 | 375 | 37 | 71 | 92 | 108 | 1.57% | 4.58% |
| test | 2022Q1-2024Q4 | 3,009 | 370 | 60 | 158 | 260 | 363 | 1.99% | 12.06% |
| **all** | | **18,000** | **948** | 251 | 639 | 1,045 | 1,457 | 1.39% | 8.09% |

Positive *firms* (rather than windows) per split:

| Split | Positive firms | Survivor firms |
|---|---:|---:|
| train | 450 | 363 |
| val | 152 | 223 |
| test | 127 | 243 |

## 3. Coverage summary

Full per-concept detail in `reports/coverage_report.md`.

| Concept group | Median coverage |
|---|---:|
| Tier-1 balance sheet and net income | 95.7% |
| Revenue and COGS | 71.6% |
| Cash flow (OCF, CapEx, D&A) | 86.0% |
| Debt aggregates | 46.5% |
| Derived earnings (EBIT, EBITDA) | 88.2% |

## 4. Known caveats

### 4.1 Interest expense
- `InterestExpense` raw coverage is 73.7% after the annual/4 fallback filled **3,579 cells** (8.8% of firm-quarters). Without the fallback it would be 64.9%.
- Ratio 13 (interest coverage) explodes near zero interest expense; the 1st/99th winsorisation clips it to [-2044, 619], the widest clipping applied to any ratio.
- Quarters where the filer reports negative or zero interest expense are left NaN rather than producing a sign-flipped coverage ratio.

### 4.2 YTD de-cumulation
| Route | Quarter-values |
|---|---:|
| reported directly as an 80-100 day quarter | 283,172 |
| reconstructed as `Qn = YTD(n) - YTD(n-1)` | 314,187 |
| reconstructed as `Q4 = FY - Q1 - Q2 - Q3` | 1,038 |
| cumulative facts not reducible to a quarter | 43,186 |

Differencing supplied **52.7%** of all flow observations. Cash-flow items are the most affected: 75% of filled OCF cells and 73% of CapEx cells are reconstructed, exactly as the spec predicts.

### 4.3 Structural sentinels
- `has_inventory = 0` for 732 firms (17,103 firm-quarters): ratios 2, 17 and 20 are NaN, not imputed.
- `has_debt = 0` for 160 firms (2,487 firm-quarters): ratio 13 is NaN.
- `r29_negative_equity_flag` is 1 in 10,228 firm-quarters (26.4% of those where equity is observed). Negative-equity rows are kept, not dropped.

### 4.4 Unmatched positives
Every labelled bankrupt firm either enters the panel or is listed in `reports/unmatched_positives.csv` with a reason. **283** of 1,066 in-window positives could not enter:

| Reason | Firms |
|---|---:|
| SIC excluded (financial 6000-6799) | 103 |
| no 10-K/10-Q with a period end in 2010-2024 | 102 |
| no entry in companyfacts.zip (never filed XBRL) | 72 |
| in scope but produced no usable firm-quarter (empty or parent-filed XBRL, or no periodic facts in the study window) | 6 |

### 4.5 Other caveats
- The pilot is deliberately positive-enriched (positives are never subsampled, and they already exceed the ~500-firm pilot budget), so the class rates above are **not** population rates.
- Survivors that stop filing for non-bankruptcy reasons (acquisition, going private, deregistration) are right-censored and labelled 0. No attempt is made to distinguish them from continuing firms.
- Flow ratios pair a quarterly flow with a point-in-time stock, so turnovers and margins are quarterly, roughly a quarter of their annual equivalents.
- Ratio 14 is the **book-value** Altman X4 (the Z'/Z" variant), not the original 1968 market-value form.
- Stride-1 windowing means input quarters near a split boundary can appear in windows on both sides; no label is shared, and `--embargo` removes those windows. See `reports/leakage_audit.md`.

## 5. Gate results

| Gate | Result | Evidence |
|---|---|---|
| Phase 1: >= 250 bankrupt firms in 2010-2024 | PASS (1,066) | `reports/labels_report.md` |
| Phase 3: coverage expectations | PASS | `reports/coverage_report.md` |
| Phase 4: hand recomputation of 5 firm-quarters | PASS | `reports/hand_check.md` |
| Phase 5: four-check leakage audit | PASS | `reports/leakage_audit.md` |
| Unit tests incl. both YTD filer styles | PASS | `pytest tests/` |

## 6. Artefact sizes

| File | Size |
|---|---:|
| `data/interim/fundamentals_panel.parquet` | 6.6 MB |
| `data/processed/ratios_panel.parquet` | 16.5 MB |
| `data/processed/sequences_train.npz` | 3.6 MB |
| `data/processed/sequences_val.npz` | 1.0 MB |
| `data/processed/sequences_test.npz` | 1.1 MB |
| `data/processed/split_manifest.csv` | 1.7 MB |
| `data/processed/labels.csv` | 0.2 MB |
| `data/processed/scaler_params.json` | 0.0 MB |

## 7. Tensor shapes

| Split | X | y | mask | indicators |
|---|---|---|---|---|
| train | (12634, 8, 29) | (12634, 4) | (12634, 8, 29) | (12634, 8, 2) |
| val | (2357, 8, 29) | (2357, 4) | (2357, 8, 29) | (2357, 8, 2) |
| test | (3009, 8, 29) | (3009, 4) | (3009, 8, 29) | (3009, 8, 2) |

`X` is z-scored with parameters fitted on 12,634 train windows only. Cells still missing after forward fill are set to the train mean (0 after standardisation) and flagged in `mask`.
