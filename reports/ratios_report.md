# Phase 4 - Ratios Report

Panel: **40,691 firm-quarters**, **1,565 firms**, 2009Q1 to 2024Q4.

## Per-ratio distributions, before and after winsorisation

Winsorisation bounds are the 1st/99th percentiles of the **training period only** (period_end <= 2019-12-31, 29,717 rows), applied to all periods.

| # | Ratio | Non-null | Cov % | Raw min | Raw p50 | Raw max | p01 bound | p99 bound | Clipped |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `r01_current_ratio` | 38,487 | 94.6 | -7.476 | 1.514 | 10,344.000 | 0.001 | 42.653 | 729 |
| 2 | `r02_quick_ratio` | 20,238 | 49.7 | -12.379 | 1.152 | 2,299.664 | 0.015 | 11.638 | 431 |
| 3 | `r03_cash_ratio` | 35,830 | 88.1 | -7.477 | 0.345 | 9,825.556 | 0.000 | 25.023 | 378 |
| 4 | `r04_wc_to_ta` | 38,384 | 94.3 | -259,884.786 | 0.095 | 287.353 | -95.248 | 0.926 | 838 |
| 5 | `r05_net_profit_margin` | 33,445 | 82.2 | -4.18e+06 | -0.048 | 1.14e+06 | -310.359 | 3.102 | 756 |
| 6 | `r06_roa` | 39,727 | 97.6 | -5.90e+08 | -0.016 | 46,834.250 | -36.762 | 0.415 | 761 |
| 7 | `r07_roe` | 38,289 | 94.1 | -5.90e+08 | 0.009 | 205,368.000 | -6.684 | 6.908 | 711 |
| 8 | `r08_ebitda_margin` | 30,518 | 75.0 | -2.92e+08 | 0.037 | 368,580.000 | -184.639 | 0.990 | 657 |
| 9 | `r09_ebit_to_ta` | 37,312 | 91.7 | -117,621.712 | -0.010 | 1.90e+08 | -20.559 | 0.180 | 709 |
| 10 | `r10_re_to_ta` | 36,607 | 90.0 | -6.73e+06 | -0.465 | 1.20e+06 | -897.891 | 1.142 | 748 |
| 11 | `r11_debt_to_equity` | 17,066 | 41.9 | -3,444.444 | 0.367 | 748,129.676 | -34.588 | 30.943 | 319 |
| 12 | `r12_debt_to_assets` | 17,682 | 43.5 | -0.811 | 0.316 | 157,059.244 | 0.000 | 6.483 | 194 |
| 13 | `r13_interest_coverage` | 26,798 | 65.9 | -2.16e+08 | -0.380 | 387,639.500 | -2,044.264 | 618.820 | 579 |
| 14 | `r14_equity_to_liabilities` | 38,692 | 95.1 | -3.30e+06 | 0.496 | 8,691.885 | -1.000 | 26.359 | 837 |
| 15 | `r15_ltd_to_ta` | 18,930 | 46.5 | -0.242 | 0.290 | 9,904.000 | 0.000 | 2.338 | 163 |
| 16 | `r16_asset_turnover` | 35,248 | 86.6 | -242.424 | 0.145 | 2.88e+09 | 0.000 | 2.200 | 499 |
| 17 | `r17_inventory_turnover` | 15,712 | 38.6 | -88.807 | 1.044 | 8,389.313 | 0.000 | 40.907 | 285 |
| 18 | `r18_receivables_turnover` | 29,202 | 71.8 | -30,749.308 | 1.952 | 72,072.756 | 0.000 | 65.689 | 456 |
| 19 | `r19_payables_turnover` | 18,962 | 46.6 | -468.962 | 1.774 | 886,463.415 | 0.000 | 27.442 | 364 |
| 20 | `r20_cash_conversion_cycle` | 12,598 | 31.0 | -1.42e+06 | 74.005 | 1.54e+06 | -2,740.341 | 1,054.974 | 298 |
| 21 | `r21_revenue_growth` | 28,199 | 69.3 | -1,228.081 | 0.024 | 392,977.200 | -1.000 | 41.631 | 399 |
| 22 | `r22_net_income_growth` | 33,682 | 82.8 | -1.10e+07 | -0.033 | 2.32e+06 | -97.522 | 18.842 | 701 |
| 23 | `r23_assets_growth` | 34,033 | 83.6 | -9.080 | 0.010 | 2.27e+10 | -0.947 | 190.651 | 628 |
| 24 | `r24_equity_growth` | 32,611 | 80.1 | -7.82e+09 | -0.025 | 26,895.900 | -27.456 | 28.485 | 649 |
| 25 | `r25_ocf_to_cl` | 37,811 | 92.9 | -77,922.772 | -0.002 | 2,800.000 | -3.477 | 8.821 | 689 |
| 26 | `r26_fcf_to_ta` | 29,201 | 71.8 | -22,059.780 | -0.007 | 4.90e+08 | -1.735 | 0.175 | 489 |
| 27 | `r27_accrual_quality` | 39,353 | 96.7 | -21,651.133 | 0.635 | 21,653.133 | -27.151 | 32.757 | 758 |
| 28 | `r28_ocf_to_debt` | 16,926 | 41.6 | -8,370.385 | 0.019 | 1.41e+06 | -22.245 | 40.267 | 330 |
| 29 | `r29_negative_equity_flag` | 38,809 | 95.4 | 0.000 | 0.000 | 1.000 | n/a | n/a | 0 |

## Missingness heatmap - % missing by ratio and year

| Ratio | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `r01_current_ratio` | 5 | 6 | 7 | 7 | 7 | 5 | 5 | 5 | 4 | 3 | 4 | 5 | 5 | 5 | 6 | 7 |
| `r02_quick_ratio` | 39 | 48 | 52 | 54 | 53 | 53 | 51 | 50 | 48 | 47 | 48 | 49 | 50 | 48 | 47 | 49 |
| `r03_cash_ratio` | 7 | 9 | 11 | 12 | 11 | 11 | 11 | 12 | 10 | 10 | 12 | 11 | 12 | 16 | 17 | 18 |
| `r04_wc_to_ta` | 5 | 6 | 7 | 7 | 7 | 6 | 6 | 5 | 4 | 4 | 4 | 5 | 6 | 6 | 6 | 8 |
| `r05_net_profit_margin` | 12 | 24 | 22 | 21 | 20 | 19 | 17 | 16 | 13 | 13 | 15 | 18 | 18 | 17 | 17 | 18 |
| `r06_roa` | 5 | 9 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 3 | 2 | 1 | 1 |
| `r07_roe` | 8 | 12 | 7 | 6 | 7 | 8 | 8 | 8 | 6 | 4 | 3 | 4 | 3 | 3 | 3 | 4 |
| `r08_ebitda_margin` | 22 | 33 | 31 | 29 | 28 | 28 | 25 | 24 | 20 | 18 | 21 | 23 | 23 | 22 | 23 | 23 |
| `r09_ebit_to_ta` | 8 | 16 | 12 | 11 | 11 | 11 | 10 | 8 | 6 | 5 | 5 | 6 | 5 | 5 | 5 | 5 |
| `r10_re_to_ta` | 7 | 13 | 18 | 18 | 17 | 15 | 10 | 8 | 7 | 6 | 5 | 5 | 5 | 4 | 4 | 5 |
| `r11_debt_to_equity` | 51 | 57 | 61 | 60 | 60 | 58 | 58 | 57 | 56 | 56 | 57 | 57 | 59 | 57 | 58 | 59 |
| `r12_debt_to_assets` | 50 | 56 | 60 | 59 | 58 | 56 | 55 | 54 | 54 | 54 | 56 | 56 | 58 | 56 | 57 | 58 |
| `r13_interest_coverage` | 18 | 35 | 36 | 35 | 36 | 35 | 35 | 34 | 31 | 31 | 32 | 32 | 35 | 35 | 35 | 36 |
| `r14_equity_to_liabilities` | 6 | 6 | 5 | 6 | 7 | 7 | 7 | 7 | 5 | 4 | 3 | 3 | 3 | 2 | 3 | 3 |
| `r15_ltd_to_ta` | 42 | 54 | 62 | 60 | 57 | 55 | 53 | 52 | 50 | 48 | 48 | 50 | 52 | 51 | 51 | 53 |
| `r16_asset_turnover` | 12 | 21 | 16 | 14 | 13 | 14 | 13 | 12 | 10 | 10 | 12 | 14 | 14 | 13 | 14 | 15 |
| `r17_inventory_turnover` | 58 | 63 | 62 | 63 | 63 | 64 | 62 | 62 | 58 | 58 | 60 | 61 | 62 | 60 | 60 | 61 |
| `r18_receivables_turnover` | 20 | 33 | 33 | 31 | 30 | 29 | 28 | 28 | 24 | 22 | 25 | 28 | 29 | 27 | 28 | 28 |
| `r19_payables_turnover` | 59 | 58 | 56 | 55 | 55 | 56 | 56 | 53 | 50 | 49 | 51 | 52 | 52 | 51 | 52 | 53 |
| `r20_cash_conversion_cycle` | 71 | 71 | 71 | 71 | 71 | 72 | 71 | 70 | 67 | 66 | 68 | 68 | 68 | 66 | 66 | 68 |
| `r21_revenue_growth` | 100 | 79 | 69 | 40 | 26 | 26 | 23 | 22 | 22 | 20 | 20 | 24 | 28 | 23 | 22 | 21 |
| `r22_net_income_growth` | 100 | 78 | 63 | 26 | 9 | 10 | 8 | 8 | 8 | 8 | 8 | 11 | 13 | 8 | 6 | 4 |
| `r23_assets_growth` | 100 | 76 | 61 | 25 | 8 | 9 | 7 | 7 | 7 | 8 | 7 | 10 | 12 | 7 | 5 | 3 |
| `r24_equity_growth` | 100 | 77 | 63 | 28 | 13 | 16 | 14 | 13 | 12 | 11 | 10 | 12 | 13 | 9 | 7 | 6 |
| `r25_ocf_to_cl` | 12 | 14 | 10 | 7 | 7 | 7 | 7 | 7 | 6 | 5 | 4 | 6 | 6 | 6 | 7 | 7 |
| `r26_fcf_to_ta` | 21 | 31 | 31 | 29 | 31 | 31 | 30 | 29 | 27 | 25 | 26 | 27 | 26 | 25 | 26 | 28 |
| `r27_accrual_quality` | 10 | 12 | 6 | 3 | 3 | 4 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 1 | 2 |
| `r28_ocf_to_debt` | 53 | 62 | 63 | 61 | 59 | 58 | 57 | 56 | 56 | 55 | 57 | 57 | 61 | 58 | 58 | 59 |
| `r29_negative_equity_flag` | 3 | 5 | 5 | 6 | 7 | 7 | 7 | 6 | 5 | 3 | 3 | 3 | 2 | 2 | 3 | 3 |

## Undefined vs missing

Structurally undefined cells are NaN and flagged, never imputed.

| Indicator | Firms = 1 | Firms = 0 | Firm-quarters = 0 |
|---|---:|---:|---:|
| `has_inventory` | 833 | 732 | 17,103 |
| `has_debt` | 1,405 | 160 | 2,487 |

| Ratio set undefined | Cells cleared |
|---|---:|
| `r02_quick_ratio` | 1,429 |
| `r17_inventory_turnover` | 900 |
| `r20_cash_conversion_cycle` | 605 |
| `r13_interest_coverage` | 0 |

`has_inventory` is 0 when inventory is absent or zero in at least 6 of the
firm's 8 most recent quarters, per the spec. `has_debt` is 0 when the firm
never reports positive total debt or positive interest expense anywhere in
its history - a recent-quarters rule would misread the many filers who tag
debt only annually.

## Conventions

- Flow ratios pair a **quarterly** flow with a point-in-time stock, so asset turnover, margins and turnovers are quarterly, roughly a quarter of their annual equivalents.
- Cash conversion cycle uses a quarter of 91.25 days: DIO = 91.25 x Inventory / COGS, DSO = 91.25 x AR / Revenue, DPO = 91.25 x AP / COGS.
- Ratio 14 uses **book** equity over total liabilities: this is the Z'/Z"
  variant of Altman X4, not the original 1968 market-value form.
- `RetainedEarningsAccumulatedDeficit` negatives are kept as reported.
- ROE and debt-to-equity are computed as-is at negative equity and left to
  winsorisation; `r29_negative_equity_flag` carries the signal explicitly and
  is excluded from winsorisation because it is binary.
