# Dataset Construction — Sources, Instructions & Ratio Derivability

**Project:** Bankruptcy Prediction using Temporal Deep Learning: A Comparative Study of LSTM and Transformer Models
**Scope recap:** Publicly listed non-financial US firms (SIC 6000–6799 excluded), quarterly data ~2010–2024, 28 financial ratios across six families, look-back window 8–10 quarters, prediction horizons 1–4 quarters. Zero/nominal data cost.

The dataset has three layers:

1. **Quarterly fundamentals** for US listed non-financial firms
2. **Bankruptcy labels** with exact event dates (needed for the 1–4Q horizons)
3. **Supplementary pre-labelled datasets** for validation and robustness checks

---

## 1. Data Sources

### 1.1 SEC EDGAR XBRL — primary fundamentals source (free, no API key)

Three access routes, easiest to most granular:

**Option A — Bulk download (recommended starting point)**
- URL: `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` (~1.2 GB, updated nightly)
- One JSON per company (keyed by CIK) containing every reported us-gaap tag across all filings.
- Steps:
  1. Download the zip and `https://www.sec.gov/files/company_tickers.json` (CIK ↔ ticker ↔ name map).
  2. Loop the JSONs, extract the required us-gaap tags, keep entries where `form` = 10-Q or 10-K, pivot to firm × quarter.

**Option B — Per-company API**
- URL pattern: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (CIK zero-padded to 10 digits)
- Use for spot checks and gap backfilling.
- Rules: set a real `User-Agent` header (e.g. `"Name email@example.com"`) — anonymous requests are blocked; stay under 10 requests/second.

**Option C — Frames API**
- URL pattern: `https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2019Q1I.json`
- Returns one tag for all filers in one quarter — useful for per-quarter coverage sanity checks.

**SIC filtering (exclude financials 6000–6799):**
- Per-firm: `https://data.sec.gov/submissions/CIK##########.json` (field `sic`), or
- Quarterly Financial Statement Data Sets: https://www.sec.gov/dera/data/financial-statement-data-sets (SIC per filing in `sub.txt`).

**Known challenge:** inconsistent tag usage across filers → a fallback tag-mapping dictionary per concept is mandatory (see Section 3).

### 1.2 Bankruptcy labels

**A. SEC full-text search — 8-K Item 1.03 "Bankruptcy or Receivership" (free)**
- UI: https://efts.sec.gov/LATEST/search-index (EDGAR full-text search frontend at https://www.sec.gov/search)
- Approach: search `"Item 1.03"` restricted to form 8-K, per year; collect CIK + filing date; treat the 8-K date as the bankruptcy event date; join to fundamentals on CIK.
- Limitation: full-text search covers 2001 onward — fine for the 2010–2024 window.

**B. Florida-UCLA-LoPucki Bankruptcy Research Database (free download)**
- URL: https://lopucki.law.ufl.edu — "Download cases table" link
- The Cases table (~200 fields) covers the ~1,000 large public company bankruptcies filed since October 1979; free to download; database updates ceased after December 2022.
- Join on CIK where available, fall back to fuzzy name matching.
- Caveats: only *large* firms (≥ $100M assets in 1980 dollars); nothing after Dec 2022. Use to validate/enrich 8-K-derived labels, not replace them.

**C. CourtListener / RECAP (free)**
- URL: https://www.courtlistener.com (API: https://www.courtlistener.com/api)
- Filter to Bankruptcy Courts, search debtor name. Only needed to cross-verify ambiguous filing dates.

### 1.3 Supplementary labelled datasets (free, instant)

**UCI Taiwanese Bankruptcy Prediction**
- https://archive.ics.uci.edu → search "Taiwanese Bankruptcy Prediction"
- 6,819 firms, 95 features. Single-snapshot — cannot feed temporal models; use for ratio-family validation and cross-market robustness.

**UCI Polish Companies Bankruptcy**
- Same repository → search "Polish companies bankruptcy"
- Five ARFF files (1–5 years before bankruptcy) → crude multi-horizon structure. Load with `scipy.io.arff` or `liac-arff`.

**Kaggle — US Company Bankruptcy Prediction Dataset**
- https://www.kaggle.com → search "US Company Bankruptcy Prediction Dataset"
- ~8,000+ NYSE/NASDAQ firms, 1999–2018, yearly accounting variables with bankruptcy labels.
- Free with a Kaggle account; download via web or CLI (`kaggle datasets download` after generating an API token in Account settings).
- Use as an independent US label check against the in-house pipeline.

### 1.4 Yahoo Finance via yfinance — market/pricing channel (free)

- Steps: `pip install yfinance`, then `yf.download(tickers, start="2010-01-01", end="2024-12-31", interval="1d")`; resample to quarterly returns and realised volatility per firm-quarter.
- **Major caveat:** Yahoo drops delisted tickers — exactly the positive class. Either pull prices before delisting while tickers still resolve, or accept the market channel covers a subset and report it as an ablation.

### 1.5 SimFin — cleaner fundamentals fallback (free tier)

- URL: https://www.simfin.com (register free for an API key); Python: `pip install simfin`, e.g. `sf.load_balance(variant='quarterly', market='us')`
- Free tier: bulk-downloadable quarterly balance sheet, P&L and cash flow data, delayed 12 months, 10+ years of history, ~5,000 US stocks. The delay is irrelevant for a 2010–2024 backtest.
- **Scope note:** the presentation promises "everything from SEC EDGAR, Kaggle and Yahoo Finance" — if SimFin becomes load-bearing, either keep it as a validation cross-check or update the scope slide.

---

## 2. Recommended Build Order

1. **Labels first:** LoPucki Cases table + 8-K Item 1.03 sweep — knowing the positive class size (~3% target) before building the fundamentals pipeline confirms the firm universe is large enough.
2. **Fundamentals second:** companyfacts.zip → ratio panel, restricted to the confirmed universe.
3. **Supplementary sets last:** UCI + Kaggle are five-minute downloads.

**Hardest join:** bankrupt-firm CIKs → fundamentals. Bankrupt firms often stop filing 2–4 quarters before the event, so the look-back window must end at the *last available filing*, not the bankruptcy date — otherwise most positives are silently dropped.

---

## 3. Ratio Derivability from SEC EDGAR — Verdict & Issues

**Verdict:** all 28 ratios are derivable, in three tiers of difficulty.

### Tier 1 — Direct single-tag lookups (low risk)

Ratios 1, 3, 4, 6, 7, 10, 14, 15, 18, 19, 23, 24 (12 ratios) come essentially free via widely-used tags (>95% coverage among non-financial filers):

| Input | Primary us-gaap tag | Fallback |
|---|---|---|
| Total Assets | `Assets` | — |
| Current Assets | `AssetsCurrent` | — |
| Current Liabilities | `LiabilitiesCurrent` | — |
| Total Liabilities | `Liabilities` | — |
| Total Equity | `StockholdersEquity` | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| Net Income | `NetIncomeLoss` | — |
| Cash & Equivalents | `CashAndCashEquivalentsAtCarryingValue` | — |
| Inventory | `InventoryNet` | — |
| Accounts Receivable | `AccountsReceivableNetCurrent` | — |
| Accounts Payable | `AccountsPayableCurrent` | — |
| Retained Earnings | `RetainedEarningsAccumulatedDeficit` | — |
| Long-Term Debt | `LongTermDebtNoncurrent` | `LongTermDebt` |

Note: `RetainedEarningsAccumulatedDeficit` is negative for accumulated-deficit firms — that is correct and predictive; do not "clean" it.

### Tier 2 — Derivable with a fallback dictionary (moderate risk)

**Revenue** (ratios 5, 8, 16, 21):
- Chain: `RevenueFromContractWithCustomerExcludingAssessedTax` → `Revenues` → `SalesRevenueNet` → `RevenueFromContractWithCustomerIncludingAssessedTax`
- The first became dominant post-ASC 606 (~2018); older filings use the latter tags. The 2010–2024 window straddles the switch, so the chain is mandatory.

**COGS** (ratios 17, 19, 20):
- Chain: `CostOfGoodsAndServicesSold` → `CostOfRevenue` → `CostOfGoodsSold` → `CostOfServices`
- Some firms report only combined operating costs — expect real gaps.

**EBIT** (ratios 9, 13):
- Practical proxy: `OperatingIncomeLoss` (good coverage). Purist EBIT (NI + interest + tax) drags in the interest-expense problem.
- Recommendation: define EBIT ≡ operating income and state it in the methodology section (consistent with the reviewed literature).

**EBITDA** (ratio 8):
- Not tagged directly. Compute: `OperatingIncomeLoss` + `DepreciationDepletionAndAmortization` (fallbacks: `DepreciationAndAmortization`, `Depreciation` + `AmortizationOfIntangibleAssets`).
- D&A sits on the cash flow statement → subject to the YTD de-cumulation trap (Tier 3).

**Total Debt** (ratios 11, 12, 28):
- No single tag. Sum: `LongTermDebtNoncurrent` + `LongTermDebtCurrent` + `ShortTermBorrowings` (fallbacks: `DebtCurrent`, `CommercialPaper`, `NotesPayableCurrent`).
- Treat missing components as zero only if the balance sheet otherwise balances, else flag.
- Alternative: `Liabilities` − `LiabilitiesCurrent` + short-term debt — overstates by including non-debt long-term liabilities (deferred tax, pensions). Pick one definition and apply uniformly.

### Tier 3 — Genuinely problematic (plan around these)

**Interest Expense (ratio 13) — the worst of the 28**
- `InterestExpense` coverage is patchy: netted into `InterestIncomeExpenseNet`, reported as `InterestExpenseDebt`, or untagged in 10-Qs for low-debt firms (annual only). Expect 20–30% missing at quarterly frequency.
- Mitigations: fall back to annual value ÷ 4, or handle via explicit imputation and report the missingness rate in the paper.
- Interest coverage explodes to ±10⁴ near zero interest expense — the 1st/99th winsorisation does heavy lifting on exactly this ratio.

**YTD de-cumulation trap (ratios 8, 25, 26, 27, 28 + EBITDA's D&A)**
- 10-Q cash flow statements are **cumulative year-to-date, not quarterly**: `NetCashProvidedByUsedInOperatingActivities` in a Q3 filing is nine months of OCF. Same for CapEx (`PaymentsToAcquirePropertyPlantAndEquipment`) and D&A.
- Reconstruction: Q1 = as reported; Q2 = YTD(Q2) − YTD(Q1); Q3 = YTD(Q3) − YTD(Q2); Q4 = 10-K annual − YTD(Q3).
- **Check `start`/`end` dates on each fact before differencing** — some filers report discrete quarters, and blind differencing double-subtracts. Filter duration facts to ~80–100 day spans; derive the rest by differencing.
- Some income statement items have the same issue (6/9-month duration facts).
- Part of the previously observed "12% of firm-quarters lacked complete cash flow items" is likely recoverable via differencing rather than truly missing.

**Structurally-missing-by-industry**
- Inventory doesn't exist for service/software firms → ratios 2, 17, 20 are *undefined*, not missing.
- Set inventory-based ratios to a neutral sentinel (or add a "has inventory" indicator) rather than imputing — otherwise the model learns imputation artifacts. Same logic for interest coverage at zero-debt firms.

### Viva footnote — Altman X₄ definition

- The specified X₄ (Total Equity / Total Liabilities) uses **book** equity → this is the **Z′-score (private-firm) variant**, not the original 1968 X₄ (market value of equity / total liabilities).
- Two clean options: (a) keep book equity and cite Z′ explicitly, or (b) since Yahoo Finance is already in scope, compute market cap = price × `CommonStockSharesOutstanding` (or `WeightedAverageNumberOfSharesOutstandingBasic`) for true X₄.
- Either is defensible — just never label the book version "Altman X₄" unqualified.

---

## 4. Bottom Line

- 12 ratios are trivial single-tag lookups.
- ~11 need the planned fallback tag dictionary (revenue, COGS, EBIT/EBITDA, total debt).
- The real engineering: (a) YTD differencing for everything cash-flow-derived, (b) the interest-expense gap, (c) undefined-vs-missing handling for inventory ratios.
- None of it blocks the project; all of it belongs in the paper's data section as evidence of honest XBRL handling.
