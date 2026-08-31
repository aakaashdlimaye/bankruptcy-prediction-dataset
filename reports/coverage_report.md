# Phase 3 - Coverage Report

Panel: **40,691 firm-quarters**, **1,565 firms**, 2009Q1 to 2024Q4.

- survivor firm-quarters: 20,751
- bankrupt-firm firm-quarters: 19,940

## Per-concept non-null coverage

`differenced %` is the share of filled cells reconstructed from cumulative
YTD facts rather than read directly as a discrete quarter.

`Coverage %` is over all firm-quarters. `Defined %` excludes structurally
absent cases - firms that never report the concept, and quarters outside a
firm's reporting span for it - so it measures whether the fallback chain
and the YTD reconstruction actually work.

| Concept | Coverage % | Defined % | Non-null | Winning tag | Tag share % | Tags used | Differenced % |
|---|---:|---:|---:|---|---:|---:|---:|
| `Assets` | 100.0 | 100.0 | 40,691 | `Assets` | 100 | 2 | 0 |
| `LiabilitiesAndStockholdersEquity` | 99.3 | 99.8 | 40,426 | `LiabilitiesAndStockholdersEquity` | 100 | 1 | 0 |
| `NetIncomeLoss` | 98.4 | 99.5 | 40,050 | `NetIncomeLoss` | 93 | 3 | 18 |
| `OCF` | 97.1 | 98.9 | 39,520 | `NetCashProvidedByUsedInOperatingActivities` | 86 | 2 | 75 |
| `Liabilities` | 96.8 | 99.6 | 39,395 | `Liabilities` | 77 | 2 | 0 |
| `AssetsCurrent` | 96.1 | 99.2 | 39,087 | `AssetsCurrent` | 100 | 1 | 0 |
| `LiabilitiesCurrent` | 95.4 | 98.9 | 38,835 | `LiabilitiesCurrent` | 100 | 1 | 0 |
| `StockholdersEquity` | 95.4 | 99.4 | 38,809 | `StockholdersEquity` | 95 | 2 | 0 |
| `StockholdersEquityInclNCI` | 95.4 | 99.4 | 38,809 | `StockholdersEquity` | 66 | 2 | 0 |
| `EBIT` | 92.3 | 98.5 | 37,550 | `OperatingIncomeLoss` | 96 | 2 | 0 |
| `CashAndEquivalents` | 91.9 | 97.7 | 37,388 | `CashAndCashEquivalentsAtCarryingValue` | 100 | 1 | 0 |
| `RetainedEarnings` | 90.7 | 98.1 | 36,903 | `RetainedEarningsAccumulatedDeficit` | 100 | 1 | 0 |
| `OperatingIncomeLoss` | 88.8 | 98.7 | 36,150 | `OperatingIncomeLoss` | 100 | 1 | 19 |
| `Revenue` | 87.0 | 97.6 | 35,392 | `Revenues` | 43 | 10 | 17 |
| `DepreciationAmortization` | 86.0 | 98.1 | 35,009 | `DepreciationDepletionAndAmortization` | 62 | 4 | 54 |
| `EBITDA` | 84.1 | 97.4 | 34,238 | `EBIT+DD&A` | 99 | 2 | 0 |
| `AccountsPayable` | 77.8 | 94.6 | 31,668 | `AccountsPayableCurrent` | 93 | 2 | 0 |
| `AccountsReceivable` | 76.1 | 94.9 | 30,959 | `AccountsReceivableNetCurrent` | 84 | 4 | 0 |
| `InterestExpense` | 73.7 | 95.7 | 30,003 | `InterestExpense` | 89 | 4 | 24 |
| `CapEx` | 72.3 | 93.4 | 29,400 | `PaymentsToAcquirePropertyPlantAndEquipment` | 86 | 3 | 73 |
| `IncomeTaxExpenseBenefit` | 70.8 | 94.4 | 28,825 | `IncomeTaxExpenseBenefit` | 100 | 1 | 25 |
| `COGS` | 56.2 | 96.6 | 22,852 | `CostOfGoodsAndServicesSold` | 42 | 4 | 24 |
| `InventoryNet` | 54.1 | 95.1 | 22,027 | `InventoryNet` | 100 | 1 | 0 |
| `CurrentDebt` | 51.4 | 81.4 | 20,912 | `LTDCur+STB` | 74 | 4 | 0 |
| `LongTermDebtNoncurrent` | 46.5 | 85.4 | 18,939 | `LongTermDebtNoncurrent` | 83 | 2 | 0 |
| `TotalDebt` | 43.6 | 78.4 | 17,738 | `LTDNoncurrent+CurrentDebt` | 87 | 2 | 0 |
| `LongTermDebtCurrent` | 37.1 | 82.8 | 15,096 | `LongTermDebtCurrent` | 82 | 2 | 0 |
| `AmortizationOfIntangibleAssets` | 31.2 | 92.8 | 12,676 | `AmortizationOfIntangibleAssets` | 100 | 1 | 35 |
| `ShortTermBorrowings` | 19.9 | 73.7 | 8,080 | `NotesPayableCurrent` | 50 | 4 | 0 |
| `DebtCurrent` | 8.0 | 86.1 | 3,238 | `DebtCurrent` | 100 | 1 | 0 |

## YTD de-cumulation

| Route | Quarter-values |
|---|---:|
| reported directly as an 80-100 day quarter | 283,172 |
| reconstructed by YTD prefix subtraction (`Qn = YTD(n) - YTD(n-1)`) | 314,187 |
| reconstructed by tiling (`Q4 = FY - Q1 - Q2 - Q3`) | 1,038 |
| cumulative facts that could not be reduced to a quarter | 43,186 |

Differencing recovered **315,225** quarter-values that would otherwise have been missing - 52.7% of all flow observations.

## Fallbacks applied

- `InterestExpense` filled from **annual / 4**: **3,579 cells** (8.8% of all firm-quarters). Without it, coverage would be 64.9%.
- `Liabilities` derived as L&SE minus NCI-inclusive equity: **9,422 cells**.
- `Assets` filled from `LiabilitiesAndStockholdersEquity` via the A = L + SE identity: **116 cells**.
- `TotalDebt` quarters left NaN because the firm tags long-term debt only annually: **5,081** (treating those as zero debt would have produced a sawtooth leverage series).

## Investigating the Revenue gap

Raw Revenue coverage is 87.0%, below the spec's 95% expectation, so
the shortfall was decomposed rather than accepted:

| Missing-Revenue firm-quarters | Count | Nature |
|---|---:|---|
| firm never reports any revenue tag | 1,629 | structural - pre-revenue development-stage filers |
| quarter precedes the firm's first reported revenue | 2,043 | structural - balance-sheet comparatives predate the income statement |
| quarter follows the firm's last reported revenue | 772 | structural - wind-down and final pre-bankruptcy quarters |
| **interior gap inside the reporting span** | **855** | **recoverable - the only genuine tagging/reconstruction loss** |

The never-reporting firms concentrate in SIC 2834/2836 (pharma and biotech),
1000/1040 (metal mining) and 1311 (oil and gas extraction), with median total
assets of $27M against $260M for revenue-reporting firms - the classic
pre-revenue profile. Their revenue is *undefined*, not missing, and is left
NaN rather than imputed as zero, which would make ratios 5, 8, 16 and 21
divide by zero.

Coverage over the population where revenue is defined is **97.6%**.

### ASC 606 tag switch

Share of filled Revenue cells by winning tag. The chain spans the 2018
transition rather than losing one regime:

| Year | `Revenues` | `SalesRevenueNet` | `RevenueFromContractWithCustomerExcludingAssessedTax` |
|---|---:|---:|---:|
| 2010 | 45% | 39% | 0% |
| 2012 | 52% | 35% | 0% |
| 2014 | 53% | 32% | 0% |
| 2016 | 53% | 31% | 1% |
| 2018 | 38% | 1% | 53% |
| 2020 | 30% | 0% | 63% |
| 2022 | 30% | 0% | 64% |
| 2024 | 26% | 0% | 69% |

## Gate

| Expectation | Observed | Verdict |
|---|---|---|
| Tier-1 concepts >= 90% | min 90.7% (`RetainedEarnings`) | PASS |
| Revenue >= 95% after fallback chain | 97.6% over the defined population (87.0% raw) | PASS |
| InterestExpense >= 70% after annual/4 | 73.7% | PASS |

**Phase 3 gate: PASS**

### Concepts below expectation that are structurally so

- `InventoryNet` (54%) and `COGS` (56%): service and software firms hold no
  inventory, and many filers report only combined operating costs (the most
  common alternative tag among the gap firms is `CostsAndExpenses`, which is
  total costs including SG&A, so it is deliberately *not* used as a COGS
  fallback). Phase 4 routes these through the `has_inventory` indicator
  rather than imputing them.
- `AccountsPayable` (78%): the common alternative is
  `AccountsPayableAndAccruedLiabilitiesCurrent`, a different concept that
  would silently inflate payables and corrupt ratio 19, so it is not used.
- `TotalDebt` (44%): many filers tag long-term debt only in the 10-K; those
  quarters are NaN rather than misreported as zero.
