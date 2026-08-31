# Judgment Calls and Their Rationale

Every non-obvious choice made while building the dataset, with a one-line
reason. Phase numbers match `prompt.md`.

---

## Phase 0 - Scaffold

| # | Decision | Rationale |
|---|---|---|
| 0.1 | Python 3.13 venv at `.venv/`, deps unpinned above minimum versions | Wheels exist for every dependency on 3.13; floating minor versions keeps the build reproducible without pinning to a platform. |
| 0.2 | All SEC traffic funnelled through `src/sec_client.py` | Centralises the mandatory User-Agent, the 8 req/s token bucket (under SEC's 10/s ceiling), retry/backoff and the on-disk cache, so no phase can accidentally violate etiquette. |
| 0.3 | Bulk files preferred over per-company API calls | Spec rule. Two downloads (companyfacts 1.41 GB, submissions 1.56 GB) replace ~20,000 API calls. |
| 0.4 | Downloads resume via HTTP Range into a `.part` file and are size-checked against `Content-Length` | Lets any interrupted run continue instead of restarting a 1.5 GB transfer. |

## Phase 1 - Bankruptcy labels

| # | Decision | Rationale |
|---|---|---|
| 1.1 | **Added a third label source**: the `items` field on every 8-K in `submissions.zip` | EDGAR records reported 8-K items structurally. This is the authoritative, non-paginated version of the full-text sweep and found 2,000 CIKs against the sweep's 1,258. |
| 1.2 | EFTS hits filtered on `_source.items` containing `"1.03"`, not on text match | The full-text query `"Item 1.03"` also matches filings that merely mention the item; the structured field is exact. |
| 1.3 | Both `8-K` and `8-K/A` accepted (EFTS `root_forms`) | Amendments frequently carry the operative bankruptcy disclosure. |
| 1.4 | Co-registrant CIKs on an Item 1.03 8-K are each recorded as bankrupt, flagged `is_primary_filer` | Co-registrants on a bankruptcy 8-K are genuinely co-debtors; each has its own fundamentals. The flag keeps the choice auditable. |
| 1.5 | **Event clustering with 365-day single linkage before any date reconciliation** | The spec's "keep the earlier date" rule is about two sources describing *one* event. Applied across a firm's whole history it destroys data: PG&E's 2019 filing was being overwritten with LoPucki's 2001 date and dropped out of the study window. Clustering keeps repeat filers (PG&E, NRG, Trump Entertainment) correct. |
| 1.6 | Firm-level `event_date` = the first event **inside 2010-2024**, not the earliest ever | A firm that went bankrupt in 2003, emerged, and filed again in 2017 contributes a usable 2017 positive; taking the earliest event would label it out-of-window and discard it. All dates retained in `all_event_dates` and `labels_events.csv`. |
| 1.7 | Name normalisation strips **only legal-form suffixes** (Inc, Corp, Ltd, LLC...), never descriptive words | An earlier version also stripped "communications", "holdings", "group" etc. That collapsed *Frontier Communications Corp* and *Frontier Holdings Inc (1986)* to the same key and produced a false 100-score match, backdating Frontier's 2020 bankruptcy to 1986. |
| 1.8 | Fuzzy match accepted at >= 90 (`token_sort_ratio`), 80-90 written to `reports/labels_fuzzy_review.csv`, below 80 unmatched | Spec thresholds. Unmatched LoPucki cases are logged in `reports/lopucki_unmatched.csv`, not silently dropped. |
| 1.9 | LoPucki cases carrying their own CIK are joined on it directly, without requiring an EDGAR 8-K match | Adds pre-full-text-era and non-8-K-filing bankruptcies that the EDGAR sweep cannot see. |
| 1.10 | Positive rate reported against the measured non-financial universe (11,962), not the assumed ~7,000 | The spec's 2-4% target assumes large continuously-listed firms; quoting a rate against a made-up denominator would be a placeholder number. The rate that matters is measured post-sequence-filter in `DATASET_REPORT.md`. |

## Phase 2 - Firm universe

| # | Decision | Rationale |
|---|---|---|
| 2.1 | Universe = 10-K/10-Q **period end** inside 2010-2024, SIC outside 6000-6799, and present in `companyfacts.zip` | Period end (not filing date) is what places a firm-quarter in the study window. The companyfacts requirement is stated explicitly rather than discovered as silent missingness later. |
| 2.2 | SIC resolution chain: submissions -> EFTS hit -> LoPucki | 189 in-scope firms have no SIC in submissions; the other two sources recover most. |
| 2.3 | Firms with no resolvable SIC are **kept and flagged**, not dropped | Dropping them would silently discard bankrupt micro-caps, biasing the positive class. |
| 2.4 | Pilot = **all** in-scope positives (789) + an equal seeded random sample of survivors (789) = 1,578 firms | The spec forbids subsampling positives, and positives alone already exceed the ~500-firm pilot budget. Survivors are matched 1:1 so coverage statistics are not read off a two-thirds-bankrupt sample. Deliberately positive-enriched; the `--full` path restores the true base rate. |

## Phase 3 - Fundamentals extraction

| # | Decision | Rationale |
|---|---|---|
| 3.1 | Calendar-quarter alignment by **nearest quarter end** | A fiscal quarter ending 31 Jan is 31 days from 31 Dec and 59 from 31 Mar, so it belongs to Q4 of the prior year. Standard Compustat-style alignment; keeps 52/53-week retail calendars in the right bucket. |
| 3.2 | Duration facts are accepted as discrete quarters only at spans of **80-100 days**; anything longer is treated as cumulative | Spec rule, and it is what makes double-subtraction impossible: a discrete-quarter fact never enters the differencing path. |
| 3.3 | Two reconstruction routes: **prefix** (`Qn = YTD(n) - YTD(n-1)`) and **tiling** (`Q4 = FY - Q1 - Q2 - Q3`) | The spec names the prefix route, which covers YTD filers. A filer reporting only discrete quarters has no cumulative prefix, so its Q4 - present in the 10-K only as an annual total - would be unrecoverable without the tiling route. Both are unit-tested. |
| 3.4 | Same-period-start matching tolerates 7 days | 52/53-week fiscal calendars shift the year start by a few days between filings. |
| 3.5 | Quarters wider than 100 days (e.g. 16-week retail Q4s) are **dropped and counted**, not widened into the quarter band | The spec fixes the band at ~80-100 days. The loss is reported rather than hidden by relaxing the rule. |
| 3.6 | Dedup priority: fiscal-year 10-K value beats a 10-Q comparative; otherwise latest filing wins | Spec rule; the 10-K is the audited version of a Q4-equivalent period. |
| 3.7 | **Panel restricted to firm-quarters with a balance-sheet anchor** (`Assets` present) | companyfacts income-statement and cash-flow comparatives reach further back than balance-sheet comparatives, creating sparse phantom rows that supported almost no ratio while depressing every coverage figure (`Assets` read 86% instead of 100%). Removing them cut 13.5% of rows and lifted all Tier-1 concepts above the 90% gate. |
| 3.8 | `Assets` falls back to `LiabilitiesAndStockholdersEquity` | A = L + SE is an identity, and filers routinely tag only one side. |
| 3.9 | `Liabilities` falls back to L&SE minus **NCI-inclusive** equity | Using parent-only equity would overstate liabilities by the non-controlling interest. |
| 3.10 | `TotalDebt`: a missing component counts as zero **only if the firm never reports it anywhere** | Many filers tag long-term debt only in the 10-K. Treating those gaps as zero turned Toys R Us's stable $4.8bn debt load into a sawtooth between $4.9bn and $0.1bn - exactly the silent corruption the spec warns about. Affected quarters are NaN instead. |
| 3.11 | When the debt chain lands on `LongTermDebt` (which already includes current maturities), only genuinely separate short-term borrowings are added | Adding `LongTermDebtCurrent` or `DebtCurrent` on top would double-count the current portion. |
| 3.12 | `DebtCurrent` combined with components as `max(DebtCurrent, LTDCurrent + STB)` | `DebtCurrent` is the total of current debt; max() avoids both double-counting it against its own components and undercounting when only some components are tagged. |
| 3.13 | **No `CostsAndExpenses` fallback for COGS** | It is total costs including SG&A. It was the most common alternative tag among firms lacking COGS, but using it would silently redefine ratios 17, 19 and 20. The gap is reported instead - the spec predicts it. |
| 3.14 | **No `AccountsPayableAndAccruedLiabilitiesCurrent` fallback for AP** | Same reasoning: it is a different concept and would inflate payables, corrupting ratio 19. |
| 3.15 | Revenue chain extended with oil & gas and regulated-utility top lines | Found by scanning pilot firms that report `Assets` but no tag from the generic chain; these are real revenue, not a definitional stretch. |
| 3.16 | `InterestExpense` chain extended with `InterestExpenseNonoperating` | The 2021+ taxonomy successor to the deprecated `InterestExpense`; without it, recent years lose coverage. `InterestIncomeExpenseNet` was **not** added - its sign convention is ambiguous and it would flip the sign of ratio 13 for an unknown subset. |
| 3.17 | Positives are audited **twice**: against the universe filters in Phase 2, and again against the finished panel in Phase 3 | Phase 2 can only test whether a CIK *has* a companyfacts entry. Six positives passed that test but produced no usable firm-quarter - their entry was an empty shell, or their XBRL is filed under a parent CIK (Pacific Gas & Electric Co vs PG&E Corp; Ferrellgas L P vs the parent partnership). Without the second audit they would have vanished silently, breaking the "every positive is either in the panel or logged with a reason" criterion. |
| 3.18 | Coverage reported both raw and over the **defined population** | Raw Revenue coverage of 87.0% decomposes into 4.0% pre-revenue firms, 6.9% quarters outside the firm's revenue-reporting span, and only 2.1% genuine interior gaps. Over the population where revenue is defined, coverage is 97.6%, which is what the spec's 95% expectation is actually about. |

## Phase 4 - Ratios

| # | Decision | Rationale |
|---|---|---|
| 4.1 | Flow ratios pair a **quarterly** flow with a point-in-time stock | The panel is quarterly, so asset turnover, margins and turnovers are quarterly magnitudes, roughly a quarter of their annual equivalents. Stated here and in the README so nobody compares them against annual benchmarks. |
| 4.2 | Cash conversion cycle uses a **91.25-day quarter**: DIO = 91.25 x Inv / COGS, DSO = 91.25 x AR / Revenue, DPO = 91.25 x AP / COGS | Direct reading of the spec's "DIO = 365/4 / quarterly inventory turnover". Using 365 with quarterly flows would inflate every component fourfold. |
| 4.3 | Division by zero yields **NaN**, not infinity | An infinite ratio is not a measurement. A zero *numerator* over a real denominator is kept as a genuine zero - the two cases are distinguished, and there is a unit test for it. |
| 4.4 | Ratio 13 is NaN when interest expense is **zero or negative** | Negative interest expense means net interest *income*; dividing by it produces a sign-flipped coverage ratio that reads as distress when the firm is fine. |
| 4.5 | Growth ratios match t-4 **on quarter index**, not by row position | The panel has gaps. A positional `shift(4)` would silently compare against t-1 wherever three quarters were missing. Unit-tested. |
| 4.6 | Growth denominators use \|x\| for revenue, net income and equity; plain TA for assets | Follows the spec's formula table. The absolute value makes a loss shrinking from -100 to -50 read as +50% improvement rather than -50%. |
| 4.7 | `has_inventory = 0` when inventory is absent **or zero** in >= 6 of the firm's 8 most recent quarters | Spec rule, with "or zero" added because some filers tag `InventoryNet = 0` explicitly rather than omitting it. Firms with fewer than 8 quarters get a proportionally scaled threshold. |
| 4.8 | `has_debt` is decided over the firm's **whole history**, not its 8 most recent quarters | The recent-quarters rule works for inventory but misreads debt: a firm tagging long-term debt only in its 10-K has three empty quarters a year and would be misclassified as debt-free. A firm counts as having debt if it ever reports positive total debt or positive interest expense. |
| 4.9 | Ratio 2 (quick ratio) is set NaN for no-inventory firms even though it is arguably defined (it equals the current ratio there) | The spec explicitly lists ratios 2, 17 and 20 as undefined without inventory. Noting the reservation rather than silently deviating; the effect is that a service firm carries three all-NaN features, which the completeness rule still tolerates. |
| 4.10 | Winsorisation fitted on `period_end <= 2019-12-31`, applied to all periods; **r29 excluded** | Spec leakage rule. Winsorising a 0/1 flag is meaningless. |
| 4.11 | Both winsorised and raw ratios are stored (`raw__` prefix) | The report needs before/after distributions, and the hand-recomputation gate must compare against unclipped values. |
| 4.12 | Hand-recomputation gate goes back to the **raw JSON**, not the panel | Recomputing from the panel would only re-test the arithmetic. Going back to companyfacts also verifies the tag selection and the de-cumulation, and the printed subtraction makes the YTD handling auditable by eye. |

## Phase 5 - Labelling and sequences

| # | Decision | Rationale |
|---|---|---|
| 5.1 | Firm-quarters with `period_end >= event_date` are **dropped entirely** | Spec rule. Post-petition financials describe a company already in bankruptcy, which is a different state from one approaching it. 3,832 firm-quarters removed. |
| 5.2 | Horizon measured in **real time** from period end: `quarters_ahead = ceil((event_date - period_end) / 91.3)`, floored at 1 | Using quarter-index arithmetic alone would assign `gap = 0` to a firm whose last period end is in the same calendar quarter as the petition, silently labelling the most imminent cases as negative. |
| 5.3 | The look-back window ends at the **last available filing**, never at the event date | The spec's dropout trap. Measured: 49% of positives stop filing at least two quarters before the petition, median gap one quarter. Anchoring to the bankruptcy date would have discarded them. |
| 5.4 | Missing quarters are materialised on a contiguous grid, then forward-filled with `limit=2` | Needed so a stride-1 window cannot silently splice non-adjacent quarters together. Rows that stay empty simply fail the completeness rule. |
| 5.5 | Forward fill cannot cross an event date | Guaranteed structurally: post-event rows are removed (5.1) before filling happens, so there is nothing on the far side to fill into. |
| 5.6 | **Completeness rule**: keep a window when, averaged over the 29 features, at least 6 of the 8 quarters are non-null | The spec asks for the exact rule to be documented. Averaging over features (rather than requiring it of every feature) is what makes service firms usable at all, since three of their features are structurally all-NaN. |
| 5.7 | The window's **end quarter must be an observed filing**, never a forward-filled placeholder | That quarter carries the label; labelling a synthetic row would invent a supervision signal. 655 windows rejected on this rule. |
| 5.8 | Split assigned by the window's **end quarter**; straddling windows are kept | Spec rule. Consequence disclosed in the leakage audit: with stride 1, input quarters near a boundary appear in windows on both sides. No label is shared. `--embargo` drops those windows for anyone wanting the stricter protocol. |
| 5.9 | Leakage check (a) is verified at the **window-index** level, `(cik, end_quarter)` | That is the unit the npz files are indexed by, and it is the only reading consistent with 5.8. The input-quarter overlap is reported separately rather than folded into a pass/fail. |
| 5.10 | Train labels reaching into the validation period are **disclosed, not silently purged** | A train window ending 2019Q4 has a y4 label resolving in 2020Q4. This is inherent to multi-horizon labelling with adjacent splits; check (d) as specified still passes, and `--embargo` is offered. Hiding it would be the wrong call. |
| 5.11 | Cells still missing after forward fill are set to the **train mean** (0 after standardisation), with a `mask` array marking them | The tensors must be numeric for the modelling stage, but the imputation must stay recoverable. The mask lets a model mask them out. |
| 5.12 | `has_inventory` / `has_debt` are shipped as a separate `indicators` array, not folded into the 29 features | The spec fixes `X` at [n, 8, 29]. Dropping the indicators would discard the information that distinguishes *undefined* from *missing*. |
| 5.13 | `X_unscaled` is also saved | Lets the modelling stage refit scaling or inspect raw magnitudes without rerunning the pipeline. |
| 5.14 | Survivors that stop filing for non-bankruptcy reasons stay labelled 0 | Distinguishing acquisition, going private and deregistration from distress needs a delisting-reason source that is not in scope. Recorded as right-censoring in the caveats. |

## Phase 6 - Supplementary datasets

| # | Decision | Rationale |
|---|---|---|
| 6.1 | UCI Taiwanese and Polish sets fetched with a **neutral User-Agent** | These are not SEC hosts. The contact email is sent only to the SEC. |
| 6.2 | Kaggle is not downloaded; instructions are written into the report and README | It requires an API token, and the spec says to write instructions and skip rather than block. `load_kaggle_us()` picks the file up automatically if it is added later. |
| 6.3 | Load-and-describe only | Spec rule; no processing beyond it. |

## Phase 7 - Deliverables

| # | Decision | Rationale |
|---|---|---|
| 7.1 | Every number in `DATASET_REPORT.md` is read from the artefacts on disk | Nothing is hard-coded, so the report cannot drift from the data or contain placeholders. |
| 7.2 | The `--full` estimate **benchmarks extraction live** on 60 firms and scales by the measured firm ratio | An extrapolation from real timings on this machine, not a guess. |
| 7.3 | `--full` writes to separate artefact paths | A full run must not overwrite the validated pilot outputs. |
| 7.4 | The full run is **not** launched | Explicit instruction: implement the flag, estimate the cost, stop. |
