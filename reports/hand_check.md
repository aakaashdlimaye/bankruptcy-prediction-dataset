# Phase 4 Gate - Hand Recomputation from Raw Facts

5 firm-quarters chosen at random (seed 42) from firm-quarters with a
complete core input set. For each one the raw XBRL facts are pulled straight
out of `companyfacts.zip`, the de-cumulation arithmetic is shown where a
value was reconstructed, all 29 ratios are recomputed longhand, and the
results are compared with `data/processed/ratios_panel.parquet`.

## QWEST CORP (CIK 68622) - 2015Q4

Fiscal period end 2015-12-31, FY FY2016.0.

### Inputs traced to raw XBRL facts

  - `Assets` <- `Assets` instant at 2015-12-31 (10-K, filed 2017-03-02) = **21.4700bn**
  - `AssetsCurrent` <- `AssetsCurrent` instant at 2015-12-31 (10-K, filed 2017-03-02) = **1.6020bn**
  - `LiabilitiesCurrent` <- `LiabilitiesCurrent` instant at 2015-12-31 (10-K, filed 2017-03-02) = **2.4220bn**
  - `Liabilities` <- `LiabilitiesAndStockholdersEquity-Equity` (derived)
  - `StockholdersEquity` <- `StockholdersEquity` instant at 2015-12-31 (10-K, filed 2018-03-12) = **8.9070bn**
  - `CashAndEquivalents` <- `CashAndCashEquivalentsAtCarryingValue` instant at 2015-12-31 (10-K, filed 2018-03-12) = **3.0000m**
  - `InventoryNet`: not populated
  - `AccountsReceivable` <- `AccountsReceivableNetCurrent` instant at 2015-12-31 (10-K, filed 2017-03-02) = **688.0000m**
  - `AccountsPayable` <- `AccountsPayableCurrent` instant at 2015-12-31 (10-K, filed 2017-03-02) = **369.0000m**
  - `RetainedEarnings` <- `RetainedEarningsAccumulatedDeficit` instant at 2015-12-31 (10-K, filed 2017-03-02) = **-1.1430bn**
  - `Revenue` <- `Revenues` reported directly for a 92-day period ending 2015-12-31 = **2.2380bn**
  - `COGS` <- `CostOfGoodsAndServicesSold` de-cumulated: YTD(2015-01-01..2015-12-31) 2.8720bn - YTD(2015-01-01..2015-09-30) 2.1690bn = **703.0000m**
  - `NetIncomeLoss` <- `NetIncomeLossAvailableToCommonStockholdersBasic` reported directly for a 92-day period ending 2015-12-31 = **321.0000m**
  - `OperatingIncomeLoss` <- `OperatingIncomeLoss` reported directly for a 92-day period ending 2015-12-31 = **622.0000m**
  - `InterestExpense` <- `InterestExpense` de-cumulated: YTD(2015-01-01..2015-12-31) 473.0000m - YTD(2015-01-01..2015-09-30) 356.0000m = **117.0000m**
  - `DepreciationAmortization` <- `DepreciationDepletionAndAmortization` de-cumulated: YTD(2015-01-01..2015-12-31) 1.8570bn - YTD(2015-01-01..2015-09-30) 1.3920bn = **465.0000m**
  - `OCF` <- `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` de-cumulated: YTD(2015-01-01..2015-12-31) 2.5910bn - YTD(2015-01-01..2015-09-30) 2.0400bn = **551.0000m**
  - `CapEx` <- `PaymentsToAcquireProductiveAssets` de-cumulated: YTD(2015-01-01..2015-12-31) 1.2470bn - YTD(2015-01-01..2015-09-30) 899.0000m = **348.0000m**
  - `LongTermDebtNoncurrent`: not populated

  - derived `EBIT` = 622.0000m, `EBITDA` = 1.0870bn, `TotalDebt` = NaN

### Ratios: hand arithmetic vs pipeline

| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |
|---|---|---|---:|---:|---|
| 1 | `r01_current_ratio` | CA / CL | 0.6614 | 0.6614 | OK |
| 2 | `r02_quick_ratio` | (CA - Inv) / CL | NaN | NaN | OK |
| 3 | `r03_cash_ratio` | Cash / CL | 0.0012 | 0.0012 | OK |
| 4 | `r04_wc_to_ta` | (CA - CL) / TA | -0.0382 | -0.0382 | OK |
| 5 | `r05_net_profit_margin` | NI / Rev | 0.1434 | 0.1434 | OK |
| 6 | `r06_roa` | NI / TA | 0.0150 | 0.0150 | OK |
| 7 | `r07_roe` | NI / Eq | 0.0360 | 0.0360 | OK |
| 8 | `r08_ebitda_margin` | EBITDA / Rev | 0.4857 | 0.4857 | OK |
| 9 | `r09_ebit_to_ta` | EBIT / TA | 0.0290 | 0.0290 | OK |
| 10 | `r10_re_to_ta` | RE / TA | -0.0532 | -0.0532 | OK |
| 11 | `r11_debt_to_equity` | Debt / Eq | NaN | NaN | OK |
| 12 | `r12_debt_to_assets` | Debt / TA | NaN | NaN | OK |
| 13 | `r13_interest_coverage` | EBIT / IntExp | 5.3162 | 5.3162 | OK |
| 14 | `r14_equity_to_liabilities` | Eq / TL | 0.7090 | 0.7090 | OK |
| 15 | `r15_ltd_to_ta` | LTD / TA | NaN | NaN | OK |
| 16 | `r16_asset_turnover` | Rev / TA | 0.1042 | 0.1042 | OK |
| 17 | `r17_inventory_turnover` | COGS / Inv | NaN | NaN | OK |
| 18 | `r18_receivables_turnover` | Rev / AR | 3.2529 | 3.2529 | OK |
| 19 | `r19_payables_turnover` | COGS / AP | 1.9051 | 1.9051 | OK |
| 20 | `r20_cash_conversion_cycle` | 91.25(Inv/COGS + AR/Rev - AP/COGS) | NaN | NaN | OK |
| 21 | `r21_revenue_growth` | (Rev - Rev_t-4) / |Rev_t-4| | 0.0067 | 0.0067 | OK |
| 22 | `r22_net_income_growth` | (NI - NI_t-4) / |NI_t-4| | 0.4861 | 0.4861 | OK |
| 23 | `r23_assets_growth` | (TA - TA_t-4) / TA_t-4 | -0.0322 | -0.0322 | OK |
| 24 | `r24_equity_growth` | (Eq - Eq_t-4) / |Eq_t-4| | -0.0301 | -0.0301 | OK |
| 25 | `r25_ocf_to_cl` | OCF / CL | 0.2275 | 0.2275 | OK |
| 26 | `r26_fcf_to_ta` | (OCF - CapEx) / TA | 0.0095 | 0.0095 | OK |
| 27 | `r27_accrual_quality` | OCF / NI | 1.7165 | 1.7165 | OK |
| 28 | `r28_ocf_to_debt` | OCF / Debt | NaN | NaN | OK |
| 29 | `r29_negative_equity_flag` | 1 if Eq < 0 | 0.0000 | 0.0000 | OK |

## Measurement Specialties Inc (CIK 778734) - 2012Q4

Fiscal period end 2012-12-31, Q3 FY2012.0.

### Inputs traced to raw XBRL facts

  - `Assets` <- `Assets` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **444.4950m**
  - `AssetsCurrent` <- `AssetsCurrent` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **151.7070m**
  - `LiabilitiesCurrent` <- `LiabilitiesCurrent` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **47.9390m**
  - `Liabilities` <- `Liabilities` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **174.1470m**
  - `StockholdersEquity` <- `StockholdersEquity` instant at 2012-12-31 (10-Q, filed 2014-02-05) = **270.3480m**
  - `CashAndEquivalents` <- `CashAndCashEquivalentsAtCarryingValue` instant at 2012-12-31 (10-Q, filed 2014-02-05) = **32.1610m**
  - `InventoryNet` <- `InventoryNet` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **60.6620m**
  - `AccountsReceivable` <- `AccountsReceivableNetCurrent` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **50.3600m**
  - `AccountsPayable` <- `AccountsPayableCurrent` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **25.5970m**
  - `RetainedEarnings` <- `RetainedEarningsAccumulatedDeficit` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **154.0860m**
  - `Revenue` <- `SalesRevenueGoodsNet` reported directly for a 92-day period ending 2012-12-31 = **81.6280m**
  - `COGS` <- `CostOfGoodsSold` reported directly for a 92-day period ending 2012-12-31 = **49.0740m**
  - `NetIncomeLoss` <- `NetIncomeLoss` reported directly for a 92-day period ending 2012-12-31 = **6.0960m**
  - `OperatingIncomeLoss` <- `OperatingIncomeLoss` reported directly for a 92-day period ending 2012-12-31 = **7.6810m**
  - `InterestExpense` <- `InterestExpense` reported directly for a 92-day period ending 2012-12-31 = **688,000.0000**
  - `DepreciationAmortization` <- `DepreciationDepletionAndAmortization` de-cumulated: YTD(2012-04-01..2012-12-31) 13.2110m - YTD(2012-04-01..2012-09-30) 8.6880m = **4.5230m**
  - `OCF` <- `NetCashProvidedByUsedInOperatingActivities` de-cumulated: YTD(2012-04-01..2012-12-31) 34.7850m - YTD(2012-04-01..2012-09-30) 22.2670m = **12.5180m**
  - `CapEx` <- `PaymentsToAcquirePropertyPlantAndEquipment` de-cumulated: YTD(2012-04-01..2012-12-31) 11.2440m - YTD(2012-04-01..2012-09-30) 8.5200m = **2.7240m**
  - `LongTermDebtNoncurrent` <- `LongTermDebtNoncurrent` instant at 2012-12-31 (10-Q, filed 2013-02-05) = **20.5380m**

  - derived `EBIT` = 7.6810m, `EBITDA` = 12.2040m, `TotalDebt` = 20.7360m

### Ratios: hand arithmetic vs pipeline

| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |
|---|---|---|---:|---:|---|
| 1 | `r01_current_ratio` | CA / CL | 3.1646 | 3.1646 | OK |
| 2 | `r02_quick_ratio` | (CA - Inv) / CL | 1.8992 | 1.8992 | OK |
| 3 | `r03_cash_ratio` | Cash / CL | 0.6709 | 0.6709 | OK |
| 4 | `r04_wc_to_ta` | (CA - CL) / TA | 0.2335 | 0.2335 | OK |
| 5 | `r05_net_profit_margin` | NI / Rev | 0.0747 | 0.0747 | OK |
| 6 | `r06_roa` | NI / TA | 0.0137 | 0.0137 | OK |
| 7 | `r07_roe` | NI / Eq | 0.0225 | 0.0225 | OK |
| 8 | `r08_ebitda_margin` | EBITDA / Rev | 0.1495 | 0.1495 | OK |
| 9 | `r09_ebit_to_ta` | EBIT / TA | 0.0173 | 0.0173 | OK |
| 10 | `r10_re_to_ta` | RE / TA | 0.3467 | 0.3467 | OK |
| 11 | `r11_debt_to_equity` | Debt / Eq | 0.0767 | 0.0767 | OK |
| 12 | `r12_debt_to_assets` | Debt / TA | 0.0467 | 0.0467 | OK |
| 13 | `r13_interest_coverage` | EBIT / IntExp | 11.1642 | 11.1642 | OK |
| 14 | `r14_equity_to_liabilities` | Eq / TL | 1.5524 | 1.5524 | OK |
| 15 | `r15_ltd_to_ta` | LTD / TA | 0.0462 | 0.0462 | OK |
| 16 | `r16_asset_turnover` | Rev / TA | 0.1836 | 0.1836 | OK |
| 17 | `r17_inventory_turnover` | COGS / Inv | 0.8090 | 0.8090 | OK |
| 18 | `r18_receivables_turnover` | Rev / AR | 1.6209 | 1.6209 | OK |
| 19 | `r19_payables_turnover` | COGS / AP | 1.9172 | 1.9172 | OK |
| 20 | `r20_cash_conversion_cycle` | 91.25(Inv/COGS + AR/Rev - AP/COGS) | 121.4974 | 121.4974 | OK |
| 21 | `r21_revenue_growth` | (Rev - Rev_t-4) / |Rev_t-4| | 0.0693 | 0.0693 | OK |
| 22 | `r22_net_income_growth` | (NI - NI_t-4) / |NI_t-4| | 0.2984 | 0.2984 | OK |
| 23 | `r23_assets_growth` | (TA - TA_t-4) / TA_t-4 | 0.1162 | 0.1162 | OK |
| 24 | `r24_equity_growth` | (Eq - Eq_t-4) / |Eq_t-4| | 0.1824 | 0.1824 | OK |
| 25 | `r25_ocf_to_cl` | OCF / CL | 0.2611 | 0.2611 | OK |
| 26 | `r26_fcf_to_ta` | (OCF - CapEx) / TA | 0.0220 | 0.0220 | OK |
| 27 | `r27_accrual_quality` | OCF / NI | 2.0535 | 2.0535 | OK |
| 28 | `r28_ocf_to_debt` | OCF / Debt | 0.6037 | 0.6037 | OK |
| 29 | `r29_negative_equity_flag` | 1 if Eq < 0 | 0.0000 | 0.0000 | OK |

## Bridgeline Digital, Inc. (CIK 1378590) - 2017Q4

Fiscal period end 2017-12-31, Q1 FY2018.0.

### Inputs traced to raw XBRL facts

  - `Assets` <- `Assets` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **18.1050m**
  - `AssetsCurrent` <- `AssetsCurrent` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **4.7890m**
  - `LiabilitiesCurrent` <- `LiabilitiesCurrent` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **3.5770m**
  - `Liabilities` <- `Liabilities` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **7.1630m**
  - `StockholdersEquity` <- `StockholdersEquity` instant at 2017-12-31 (10-Q, filed 2019-08-14) = **10.9420m**
  - `CashAndEquivalents` <- `CashAndCashEquivalentsAtCarryingValue` instant at 2017-12-31 (10-Q, filed 2019-02-14) = **1.1170m**
  - `InventoryNet`: not populated
  - `AccountsReceivable` <- `AccountsReceivableGrossCurrent` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **3.2940m**
  - `AccountsPayable` <- `AccountsPayableCurrent` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **1.1750m**
  - `RetainedEarnings` <- `RetainedEarningsAccumulatedDeficit` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **-54.7540m**
  - `Revenue` <- `RevenueFromContractWithCustomerExcludingAssessedTax` reported directly for a 92-day period ending 2017-12-31 = **3.9690m**
  - `COGS` <- `CostOfGoodsAndServicesSold` reported directly for a 92-day period ending 2017-12-31 = **1.9570m**
  - `NetIncomeLoss` <- `NetIncomeLoss` reported directly for a 92-day period ending 2017-12-31 = **-430,000.0000**
  - `OperatingIncomeLoss` <- `OperatingIncomeLoss` reported directly for a 92-day period ending 2017-12-31 = **-343,000.0000**
  - `InterestExpense`: not populated
  - `DepreciationAmortization` <- `DepreciationDepletionAndAmortization` reported directly for a 92-day period ending 2017-12-31 = **108,000.0000**
  - `OCF` <- `NetCashProvidedByUsedInOperatingActivities` reported directly for a 92-day period ending 2017-12-31 = **-575,000.0000**
  - `CapEx` <- `PaymentsToAcquirePropertyPlantAndEquipment` reported directly for a 92-day period ending 2017-12-31 = **8,000.0000**
  - `LongTermDebtNoncurrent` <- `LongTermDebtNoncurrent` instant at 2017-12-31 (10-Q, filed 2018-02-14) = **3.1420m**

  - derived `EBIT` = -343,000.0000, `EBITDA` = -235,000.0000, `TotalDebt` = 3.1840m

### Ratios: hand arithmetic vs pipeline

| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |
|---|---|---|---:|---:|---|
| 1 | `r01_current_ratio` | CA / CL | 1.3388 | 1.3388 | OK |
| 2 | `r02_quick_ratio` | (CA - Inv) / CL | NaN | NaN | OK |
| 3 | `r03_cash_ratio` | Cash / CL | 0.3123 | 0.3123 | OK |
| 4 | `r04_wc_to_ta` | (CA - CL) / TA | 0.0669 | 0.0669 | OK |
| 5 | `r05_net_profit_margin` | NI / Rev | -0.1083 | -0.1083 | OK |
| 6 | `r06_roa` | NI / TA | -0.0238 | -0.0238 | OK |
| 7 | `r07_roe` | NI / Eq | -0.0393 | -0.0393 | OK |
| 8 | `r08_ebitda_margin` | EBITDA / Rev | -0.0592 | -0.0592 | OK |
| 9 | `r09_ebit_to_ta` | EBIT / TA | -0.0189 | -0.0189 | OK |
| 10 | `r10_re_to_ta` | RE / TA | -3.0242 | -3.0242 | OK |
| 11 | `r11_debt_to_equity` | Debt / Eq | 0.2910 | 0.2910 | OK |
| 12 | `r12_debt_to_assets` | Debt / TA | 0.1759 | 0.1759 | OK |
| 13 | `r13_interest_coverage` | EBIT / IntExp | NaN | NaN | OK |
| 14 | `r14_equity_to_liabilities` | Eq / TL | 1.5276 | 1.5276 | OK |
| 15 | `r15_ltd_to_ta` | LTD / TA | 0.1735 | 0.1735 | OK |
| 16 | `r16_asset_turnover` | Rev / TA | 0.2192 | 0.2192 | OK |
| 17 | `r17_inventory_turnover` | COGS / Inv | NaN | NaN | OK |
| 18 | `r18_receivables_turnover` | Rev / AR | 1.2049 | 1.2049 | OK |
| 19 | `r19_payables_turnover` | COGS / AP | 1.6655 | 1.6655 | OK |
| 20 | `r20_cash_conversion_cycle` | 91.25(Inv/COGS + AR/Rev - AP/COGS) | NaN | NaN | OK |
| 21 | `r21_revenue_growth` | (Rev - Rev_t-4) / |Rev_t-4| | -0.0055 | -0.0055 | OK |
| 22 | `r22_net_income_growth` | (NI - NI_t-4) / |NI_t-4| | -0.0539 | -0.0539 | OK |
| 23 | `r23_assets_growth` | (TA - TA_t-4) / TA_t-4 | -0.0138 | -0.0138 | OK |
| 24 | `r24_equity_growth` | (Eq - Eq_t-4) / |Eq_t-4| | -0.0938 | -0.0938 | OK |
| 25 | `r25_ocf_to_cl` | OCF / CL | -0.1607 | -0.1607 | OK |
| 26 | `r26_fcf_to_ta` | (OCF - CapEx) / TA | -0.0322 | -0.0322 | OK |
| 27 | `r27_accrual_quality` | OCF / NI | 1.3372 | 1.3372 | OK |
| 28 | `r28_ocf_to_debt` | OCF / Debt | -0.1806 | -0.1806 | OK |
| 29 | `r29_negative_equity_flag` | 1 if Eq < 0 | 0.0000 | 0.0000 | OK |

## UNIROYAL GLOBAL ENGINEERED PRODUCTS, INC. (CIK 1172706) - 2015Q1

Fiscal period end 2015-04-05, Q1 FY2016.0.

### Inputs traced to raw XBRL facts

  - `Assets` <- `Assets` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **56.7788m**
  - `AssetsCurrent` <- `AssetsCurrent` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **37.7712m**
  - `LiabilitiesCurrent` <- `LiabilitiesCurrent` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **32.9439m**
  - `Liabilities` <- `Liabilities` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **45.9867m**
  - `StockholdersEquity` <- `StockholdersEquity` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **10.7921m**
  - `CashAndEquivalents` <- `CashAndCashEquivalentsAtCarryingValue` instant at 2015-04-05 (10-Q, filed 2016-05-05) = **2.1385m**
  - `InventoryNet` <- `InventoryNet` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **17.1473m**
  - `AccountsReceivable` <- `AccountsReceivableNetCurrent` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **16.3541m**
  - `AccountsPayable` <- `AccountsPayableCurrent` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **9.9120m**
  - `RetainedEarnings` <- `RetainedEarningsAccumulatedDeficit` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **-25.9091m**
  - `Revenue` <- `SalesRevenueNet` reported directly for a 90-day period ending 2015-04-05 = **27.5149m**
  - `COGS` <- `CostOfGoodsSold` reported directly for a 90-day period ending 2015-04-05 = **22.1599m**
  - `NetIncomeLoss` <- `NetIncomeLoss` reported directly for a 90-day period ending 2015-04-05 = **1.4107m**
  - `OperatingIncomeLoss` <- `OperatingIncomeLoss` reported directly for a 90-day period ending 2015-04-05 = **1.7455m**
  - `InterestExpense` <- `InterestExpense` reported directly for a 90-day period ending 2015-04-05 = **370,822.0000**
  - `DepreciationAmortization` <- `Depreciation` reported directly for a 90-day period ending 2015-04-05 = **387,843.0000**
  - `OCF` <- `NetCashProvidedByUsedInOperatingActivities` reported directly for a 90-day period ending 2015-04-05 = **405,939.0000**
  - `CapEx` <- `PaymentsToAcquirePropertyPlantAndEquipment` reported directly for a 90-day period ending 2015-04-05 = **1.5057m**
  - `LongTermDebtNoncurrent` <- `LongTermDebt` instant at 2015-04-05 (10-Q, filed 2015-05-04) = **1.1975m**

  - derived `EBIT` = 1.7455m, `EBITDA` = 2.1334m, `TotalDebt` = 1.1975m

### Ratios: hand arithmetic vs pipeline

| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |
|---|---|---|---:|---:|---|
| 1 | `r01_current_ratio` | CA / CL | 1.1465 | 1.1465 | OK |
| 2 | `r02_quick_ratio` | (CA - Inv) / CL | 0.6260 | 0.6260 | OK |
| 3 | `r03_cash_ratio` | Cash / CL | 0.0649 | 0.0649 | OK |
| 4 | `r04_wc_to_ta` | (CA - CL) / TA | 0.0850 | 0.0850 | OK |
| 5 | `r05_net_profit_margin` | NI / Rev | 0.0513 | 0.0513 | OK |
| 6 | `r06_roa` | NI / TA | 0.0248 | 0.0248 | OK |
| 7 | `r07_roe` | NI / Eq | 0.1307 | 0.1307 | OK |
| 8 | `r08_ebitda_margin` | EBITDA / Rev | 0.0775 | 0.0775 | OK |
| 9 | `r09_ebit_to_ta` | EBIT / TA | 0.0307 | 0.0307 | OK |
| 10 | `r10_re_to_ta` | RE / TA | -0.4563 | -0.4563 | OK |
| 11 | `r11_debt_to_equity` | Debt / Eq | 0.1110 | 0.1110 | OK |
| 12 | `r12_debt_to_assets` | Debt / TA | 0.0211 | 0.0211 | OK |
| 13 | `r13_interest_coverage` | EBIT / IntExp | 4.7072 | 4.7072 | OK |
| 14 | `r14_equity_to_liabilities` | Eq / TL | 0.2347 | 0.2347 | OK |
| 15 | `r15_ltd_to_ta` | LTD / TA | 0.0211 | 0.0211 | OK |
| 16 | `r16_asset_turnover` | Rev / TA | 0.4846 | 0.4846 | OK |
| 17 | `r17_inventory_turnover` | COGS / Inv | 1.2923 | 1.2923 | OK |
| 18 | `r18_receivables_turnover` | Rev / AR | 1.6824 | 1.6824 | OK |
| 19 | `r19_payables_turnover` | COGS / AP | 2.2357 | 2.2357 | OK |
| 20 | `r20_cash_conversion_cycle` | 91.25(Inv/COGS + AR/Rev - AP/COGS) | 84.0300 | 84.0300 | OK |
| 21 | `r21_revenue_growth` | (Rev - Rev_t-4) / |Rev_t-4| | 0.1290 | 0.1290 | OK |
| 22 | `r22_net_income_growth` | (NI - NI_t-4) / |NI_t-4| | 1.3678 | 1.3678 | OK |
| 23 | `r23_assets_growth` | (TA - TA_t-4) / TA_t-4 | 1,394.7074 | 1,394.7074 | OK |
| 24 | `r24_equity_growth` | (Eq - Eq_t-4) / |Eq_t-4| | 9.1089 | 9.1089 | OK |
| 25 | `r25_ocf_to_cl` | OCF / CL | 0.0123 | 0.0123 | OK |
| 26 | `r26_fcf_to_ta` | (OCF - CapEx) / TA | -0.0194 | -0.0194 | OK |
| 27 | `r27_accrual_quality` | OCF / NI | 0.2878 | 0.2878 | OK |
| 28 | `r28_ocf_to_debt` | OCF / Debt | 0.3390 | 0.3390 | OK |
| 29 | `r29_negative_equity_flag` | 1 if Eq < 0 | 0.0000 | 0.0000 | OK |

## SOURCEFIRE INC (CIK 1168195) - 2011Q4

Fiscal period end 2011-12-31, FY FY2012.0.

### Inputs traced to raw XBRL facts

  - `Assets` <- `Assets` instant at 2011-12-31 (10-K, filed 2013-02-28) = **283.9270m**
  - `AssetsCurrent` <- `AssetsCurrent` instant at 2011-12-31 (10-K, filed 2013-02-28) = **196.9010m**
  - `LiabilitiesCurrent` <- `LiabilitiesCurrent` instant at 2011-12-31 (10-K, filed 2013-02-28) = **74.4150m**
  - `Liabilities` <- `Liabilities` instant at 2011-12-31 (10-K, filed 2013-02-28) = **86.0700m**
  - `StockholdersEquity` <- `StockholdersEquity` instant at 2011-12-31 (10-K, filed 2013-02-28) = **197.8570m**
  - `CashAndEquivalents` <- `CashAndCashEquivalentsAtCarryingValue` instant at 2011-12-31 (10-K, filed 2013-02-28) = **59.4070m**
  - `InventoryNet` <- `InventoryNet` instant at 2011-12-31 (10-K, filed 2013-02-28) = **4.2850m**
  - `AccountsReceivable`: not populated
  - `AccountsPayable` <- `AccountsPayableCurrent` instant at 2011-12-31 (10-K, filed 2013-02-28) = **5.4070m**
  - `RetainedEarnings` <- `RetainedEarningsAccumulatedDeficit` instant at 2011-12-31 (10-K, filed 2013-02-28) = **-15.5490m**
  - `Revenue` <- `SalesRevenueNet` reported directly for a 92-day period ending 2011-12-31 = **53.2040m**
  - `COGS` <- `CostOfGoodsAndServicesSold` de-cumulated: YTD(2011-01-01..2011-12-31) 37.2090m - YTD(2011-01-01..2011-09-30) 24.9180m = **12.2910m**
  - `NetIncomeLoss` <- `ProfitLoss` reported directly for a 92-day period ending 2011-12-31 = **4.1340m**
  - `OperatingIncomeLoss` <- `OperatingIncomeLoss` reported directly for a 92-day period ending 2011-12-31 = **6.7380m**
  - `InterestExpense`: not populated
  - `DepreciationAmortization` <- `DepreciationDepletionAndAmortization` de-cumulated: YTD(2011-01-01..2011-12-31) 5.2800m - YTD(2011-01-01..2011-09-30) 3.8730m = **1.4070m**
  - `OCF` <- `NetCashProvidedByUsedInOperatingActivities` de-cumulated: YTD(2011-01-01..2011-12-31) 14.6020m - YTD(2011-01-01..2011-09-30) -421,000.0000 = **15.0230m**
  - `CapEx` <- `PaymentsToAcquirePropertyPlantAndEquipment` de-cumulated: YTD(2011-01-01..2011-12-31) 6.5110m - YTD(2011-01-01..2011-09-30) 4.3440m = **2.1670m**
  - `LongTermDebtNoncurrent`: not populated

  - derived `EBIT` = 6.7380m, `EBITDA` = 8.1450m, `TotalDebt` = NaN

### Ratios: hand arithmetic vs pipeline

| # | Ratio | Hand computation | Hand value | Pipeline (raw) | Match |
|---|---|---|---:|---:|---|
| 1 | `r01_current_ratio` | CA / CL | 2.6460 | 2.6460 | OK |
| 2 | `r02_quick_ratio` | (CA - Inv) / CL | 2.5884 | 2.5884 | OK |
| 3 | `r03_cash_ratio` | Cash / CL | 0.7983 | 0.7983 | OK |
| 4 | `r04_wc_to_ta` | (CA - CL) / TA | 0.4314 | 0.4314 | OK |
| 5 | `r05_net_profit_margin` | NI / Rev | 0.0777 | 0.0777 | OK |
| 6 | `r06_roa` | NI / TA | 0.0146 | 0.0146 | OK |
| 7 | `r07_roe` | NI / Eq | 0.0209 | 0.0209 | OK |
| 8 | `r08_ebitda_margin` | EBITDA / Rev | 0.1531 | 0.1531 | OK |
| 9 | `r09_ebit_to_ta` | EBIT / TA | 0.0237 | 0.0237 | OK |
| 10 | `r10_re_to_ta` | RE / TA | -0.0548 | -0.0548 | OK |
| 11 | `r11_debt_to_equity` | Debt / Eq | NaN | NaN | OK |
| 12 | `r12_debt_to_assets` | Debt / TA | NaN | NaN | OK |
| 13 | `r13_interest_coverage` | EBIT / IntExp | NaN | NaN | OK |
| 14 | `r14_equity_to_liabilities` | Eq / TL | 2.2988 | 2.2988 | OK |
| 15 | `r15_ltd_to_ta` | LTD / TA | NaN | NaN | OK |
| 16 | `r16_asset_turnover` | Rev / TA | 0.1874 | 0.1874 | OK |
| 17 | `r17_inventory_turnover` | COGS / Inv | 2.8684 | 2.8684 | OK |
| 18 | `r18_receivables_turnover` | Rev / AR | NaN | NaN | OK |
| 19 | `r19_payables_turnover` | COGS / AP | 2.2732 | 2.2732 | OK |
| 20 | `r20_cash_conversion_cycle` | 91.25(Inv/COGS + AR/Rev - AP/COGS) | NaN | NaN | OK |
| 21 | `r21_revenue_growth` | (Rev - Rev_t-4) / |Rev_t-4| | 0.4012 | 0.4012 | OK |
| 22 | `r22_net_income_growth` | (NI - NI_t-4) / |NI_t-4| | -0.0613 | -0.0613 | OK |
| 23 | `r23_assets_growth` | (TA - TA_t-4) / TA_t-4 | 0.1778 | 0.1778 | OK |
| 24 | `r24_equity_growth` | (Eq - Eq_t-4) / |Eq_t-4| | 0.1913 | 0.1913 | OK |
| 25 | `r25_ocf_to_cl` | OCF / CL | 0.2019 | 0.2019 | OK |
| 26 | `r26_fcf_to_ta` | (OCF - CapEx) / TA | 0.0453 | 0.0453 | OK |
| 27 | `r27_accrual_quality` | OCF / NI | 3.6340 | 3.6340 | OK |
| 28 | `r28_ocf_to_debt` | OCF / Debt | NaN | NaN | OK |
| 29 | `r29_negative_equity_flag` | 1 if Eq < 0 | 0.0000 | 0.0000 | OK |

## Verdict

**PASS** - all 29 ratios matched to a relative tolerance of 1e-06 on every sampled firm-quarter.
