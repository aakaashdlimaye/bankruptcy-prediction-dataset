# Capstone Project — Session Notes

**Project:** Bankruptcy Prediction using Temporal Deep Learning: A Comparative Study of LSTM and Transformer Models
**Student:** Harshit Bhinde (E006)
**Team:** Manognaa Vakkalanka (E072) · Harshit Bhinde (E006) · Aakaash D Limaye (E032) · PV Krishna Teja (E068)
**Programme:** B.Tech, Computer Science and Business Systems, Semester VII
**Institution:** Mukesh Patel School of Technology Management & Engineering, SVKM's NMIMS
**Faculty Mentor:** Prof. Deepali Maste
**A.Y.:** 2026–2027

---

## Table of Contents

1. [Core Project Idea](#1-core-project-idea)
2. [Literature Review — 21 Papers](#2-literature-review--21-papers)
3. [The Research Gap](#3-the-research-gap)
4. [The Refined Idea — Decomposition Experiment](#4-the-refined-idea--decomposition-experiment)
5. [Feature Set — All 28 Ratios](#5-feature-set--all-28-ratios)
6. [Architecture and Implementation Spec](#6-architecture-and-implementation-spec)
7. [Contributions and Target Venues](#7-contributions-and-target-venues)
8. [Presentation — Structure, Splits, Script](#8-presentation--structure-splits-script)
9. [In-Depth Explanation of Slides 5–8](#9-in-depth-explanation-of-slides-58)
10. [Logbook Entries — 7 Fortnights](#10-logbook-entries--7-fortnights)
11. [IEEE Search Keywords](#11-ieee-search-keywords)
12. [Deliverables and Open Questions](#12-deliverables-and-open-questions)

---

## 1. Core Project Idea

Bankruptcy prediction using deep learning applied to **temporal sequences of quarterly financial ratios**, rather than single-period snapshots.

> Bankruptcy is a **process**, not an event. Firms deteriorate across quarters — revenue falls, debt rises, interest cover thins. Every model in current use throws that sequence away and scores a firm from one snapshot. We model the sequence instead, and show which quarters carried the warning.

**Architectures (in build order):**

1. LSTM (baseline)
2. Bidirectional LSTM
3. Transformer encoder — primary model
4. CNN-LSTM-Attention hybrid — most advanced variant

**Input:** 28 financial ratios per firm-quarter across six families. Look-back window 8 quarters, stride 1; prediction horizon 1–4 quarters ahead.

**Interpretability:** attention weights identify which quarters and ratios drove the prediction; SHAP group importance as an independent cross-check.

**Data:** SEC EDGAR (XBRL), Kaggle/UCI labelled bankruptcy datasets, Yahoo Finance. All free.

**Target:** Scopus-indexed publication; 14-week schedule; zero data and compute cost.

---

## 2. Literature Review — 21 Papers

### Set A — Elsevier journals (10 papers)

| # | Paper Title | Author | Technique Used | Challenges / Limitations | Future Work |
|---|---|---|---|---|---|
| 1 | Machine learning for corporate default risk: Multi-period prediction, frailty correlation, loan portfolios, and tail probabilities (EJOR 305, 2023) | Sigrist & Leuenberger | Tree-boosting + latent frailty model ("LaGaBoost"), benchmarked against linear/mixed-effects hazard models; SHAP | Predictors capture a single time point only; frailty correlation across forward periods not modelled; unexplained temporal variation in tail predictions | **Add lagged information to predictors**; extend other ML techniques to include frailty; model frailty correlation across periods |
| 2 | A transformer-based model for default prediction in mid-cap corporate markets (EJOR 308, 2023) | Korangi, Mues & Bravo | Transformer encoder (TEP) on multi-channel panel data; multi-label term-structure classification; benchmarked vs LSTM/TCN; Shapley + attention heat maps | Independence assumption among multi-label outcomes not enforced; interpretability only at variable-group level; no text data | Add management/news/media channels; use attention-highlighted features in simpler models; refine multi-horizon loss weighting |
| 3 | The evaluation of bankruptcy prediction models based on socio-economic costs (ESWA 227, 2023) | Radovanovic & Haas | RF, boosted trees, SVM, LR, NN, discriminant analysis evaluated with cost-based metrics (financial cost, job-loss proxy) | Financial data only; cannot separate temporary distress from true bankruptcy; cannot evaluate Type II impact on the firm; accuracy degrades across periods | Combine textual, macroeconomic and governance variables; study asymmetric Type I vs Type II impact |
| 4 | Bankruptcy prediction using ML models with the text-based communicative value of annual reports (ESWA 233, 2023) | Chen, Liao, Chen, Kang & Lin | LR / RF / XGBoost / SVM + annual-report "communicative value"; EasyEnsemble and BalancedBaggingClassifier | Severe imbalance (2.2% bankrupt; 40,507 vs 932); confidential dataset limits replication; proxy may not generalise beyond US 10-Ks | Introduce other non-financial variables; alternative feature selection and boosting/bagging methods |
| 5 | Gamma–Lindley regression cure model for corporate credit default prediction (ESWA 257, 2024) | Chakroun, Abid, Elarbi & Masmoudi | Survival analysis — Gamma–Lindley mixture cure model + LR/K-means; benchmarked vs Exponential/Gamma/Weibull/Cox PH | Purely parametric; classification limited to LR and K-means | Consider additive hazards; incorporate tree-based and other clustering classifiers |
| 6 | Multi-class financial distress prediction based on hybrid feature selection and improved stacking ensemble (ESWA 282, 2025) | Chen, Liu & Wu | Information Gain + improved PSO feature selection; stacking ensemble tuned via Hyperopt and constrained GA | Chinese listed firms only; IG captures linear correlation only; high computational cost | Multi-country/multi-industry data; nonlinear feature evaluation; lightweight stacking architecture |
| 7 | Prediction of corporate default risk considering ESG performance and unbalanced samples (ASOC 171, 2025) | Chang, Liu & Deng | Stacking + Focal Loss + cost-sensitive threshold; ESG composite/E/S/G scores as features | Chinese A-share only; short ESG window (2021–2023) | Apply CS-FL-Stacking to other imbalanced domains (future-work text truncated in source PDF) |
| 8 | Financial distress prediction based on deep learning model (Procedia CS 243, 2024) | Sun | Five-layer feedforward network (23-18-14-10-5-2) on 23 indicators; vs LR and BP neural network | Single-period input, no sequence modelling; no imbalance treatment; limited evaluation | Not stated |
| 9 | An intelligent bankruptcy prediction model using a multilayer perceptron (ISWA 16, 2022) | Förch Brenes, Johannssen & Chukhrova | MLP with optimiser/architecture sweep; survey of 500+ prior studies; Taiwanese data | Small, highly imbalanced dataset; ANN/SVM lack transparency; dimensionality risk with qualitative variables | Larger/balanced datasets; sector-separated models; variables predictive 2–3 years ahead; better ANN/SVM interpretability |
| 10 | Multi-modal bankruptcy risk prediction for listed companies via large language models (Information Sciences 744, 2026) | Xiong, Jiang, Yu, Fang, Zhao, Liu & Wang | SLMNN: LLM-inferred risk-correlation edge weights + GNN; dual cross-/intra-modal attention; high-frequency graph convolution with semantic gating | Only the abstract page was obtained — full PDF not downloaded | Not available |

### Set B — IEEE Xplore (11 papers)

| # | Paper | Venue | Method | Data | Reported |
|---|---|---|---|---|---|
| 11 | Tikkhaviro & Lukman (2026) | IEHNS | RF, LR, XGBoost | 80 Indonesian firms (40 bankrupt / 40 not), 2015–Q1 2025 | 93% acc (XGB, RF); 86.7% (LR) |
| 12 | Rosli, Zuber, Canda & Abdul Wahab (2025) | ICERCS | Random Forest, 9 ratios selected from 96 | Taiwanese (UCI) | ~95% acc |
| 13 | He (2025) | ICSECE | Hierarchical GNN: GCN + 4-head GAT + gated fusion | A-share listed companies | 0.91 acc, 0.85 F1, +8.97% over XGBoost |
| 14 | Huang (2025) | ISCBI | Stacked Autoencoder + Softmax classifier | Polish (UCI), 5 years of ratios | — |
| 15 | Arya, Soni, Uppal & Saini (2024) | ICAICCIT | Voting classifier (LR + DT + SVM) | UCI | 97% acc |
| 16 | Khudhur (2024) | OIDT | ANN vs Random Forest | Taiwanese, 6,819 firms, 79 ratios, 1999–2009 | ~96.6% acc |
| 17 | Sabri, Md Sahiq, Mohamed Hamzah, Sain, Abu Mangshor & Shari (2024) | SCOReD | SVM — *individual* bankruptcy, Malaysian M40 income group | Survey data | 91.1% acc |
| 18 | Murugan, Le, Nguyen, Pham, Nguyen & Le (2023) | ICSSE | Function-Link Cerebellar Model Neural Network (FL-CMNN) | Taiwanese (UCI) | — |
| 19 | Rout & Nayak (2023) | OCIT | GAN oversampling + Genetic Algorithm feature selection; SVM/RF/DT/LR | UCI | RF best; GA beats Chi-square and Backward Elimination |
| 20 | Kothuru, Jha, Ranjit, Reddy, Roy & Sudheer (2022) | ICESC | General ML comparison | Taiwanese | — |
| 21 | Vinogradova, Lazarev & Kharlamov (2021) | REEPE | ML + neural networks + fuzzy models to **forecast Altman Z-score values** | Russian fuel & energy sector | — |

**Verdict: all 21 are usable for the literature review.** None are off-topic.

**Notes:**

- **Korangi et al. (#2)** is the closest technical predecessor. Read most carefully; expect panel questions comparing your work to it.
- **Förch Brenes et al. (#9)** contains a survey of 500+ studies since the 1930s — cite it for the historical arc instead of reading fifty papers.
- **Xiong et al. (#10)** — only the ScienceDirect abstract page was saved. Download the full PDF if citing methodology in detail.
- **Chang et al. (#7)** — future-work paragraph is cut off mid-sentence in the source PDF (column-break extraction artifact).
- **Vinogradova et al. (#21)** is the closest prior attempt to combine Altman with learned models. Distinguish yourself by predicting bankruptcy directly rather than forecasting the score.

---

## 3. The Research Gap

### What the literature has settled

1. **ML beats linear scoring** — papers 1, 3, 9, across different datasets and continents. Don't waste slides re-proving it.
2. **Imbalance handling materially changes results** — papers 4, 7. Not a preprocessing detail; it changes which model appears best.
3. **Evaluation should reflect economic cost** — paper 3, demonstrated empirically.
4. **Deep models win when given true panel data** — paper 2. Crucially, only *when temporal structure is preserved*. Every paper that flattens panel data into cross-sections finds gradient boosting wins.

That asymmetry is the intellectual core: deep learning doesn't beat XGBoost on tabular data — it beats it on *sequences*. So the contribution must be about the sequence, not about being deep.

### What remains open

1. **Most models consume a single snapshot** — papers 1, 5, 8, 9, and all eleven IEEE papers.
2. **Across 21 papers, exactly one uses a sequence model** (Korangi et al.). Zero use LSTM. Zero benchmark LSTM against Transformer.
3. **Which quarters signal failure is unanswered** — paper 2 produces attention heat maps but treats them as a by-product.
4. **No cross-architecture comparison under one protocol** — same dataset, same chronological split, same imbalance treatment, same tuning budget, same metrics. Without holding those constant, comparing AUCs across papers is meaningless.

Point 4 is the safest claim: points 1–3 could be disputed with a missed paper; point 4 is a statement about the *structure* of the literature.

### Two findings from the IEEE set that strengthen the case

**1. Two IEEE papers explicitly ask for what we're building.**

- Tikkhaviro & Lukman (2026): future work should expand the database "to contain more than one year's worth of data on each company in order to obtain a more thorough understanding of the temporal aspect."
- He (2025): future work should build "a dynamic graph learning framework… to adapt to the temporal evolution characteristics."

We are answering stated calls from 2025 and 2026 papers, not inventing a gap.

**2. The reported accuracies are not credible — and that is an opening.**

Eight of eleven IEEE papers report 91–99% accuracy. Those numbers come from three sources:

- **Accuracy on imbalanced data.** At a 3% base rate, predicting "healthy" for everyone scores 97%. Khudhur admits the imbalance and still headlines 96.6%.
- **Artificially balanced samples.** Tikkhaviro & Lukman use 40 bankrupt and 40 healthy firms. That is not the world.
- **Random rather than chronological splits.** None of the eleven state a time-aware split. A random split lets the model see 2023 data while predicting 2019 — look-ahead leakage that inflates every metric.

Seven of eleven also use the same UCI Taiwanese dataset — 6,819 firms, 1999–2009, **cross-sectional**. Temporal work on it is structurally impossible. That single fact explains why the gap exists, and justifies the SEC EDGAR panel construction as a contribution in its own right.

---

## 4. The Refined Idea — Decomposition Experiment

Don't frame the paper as "LSTM beats Altman." Frame it as a **decomposition**: *why* does a 1968 formula still underperform, and which part of it is actually broken?

| Model | Variables | Coefficients | Temporal | Isolates |
|---|---|---|---|---|
| **A. Altman Z-score** | Altman's 5 | Fixed, 1968 | Static | Baseline |
| **B. Re-estimated Altman** | Altman's 5 | Re-fit on training window | Static | Are the *coefficients* stale? |
| **C. Altman-variable LSTM** | Altman's 5 | Learned | 8-quarter sequence | Is the *static formulation* the problem? |
| **D. Full temporal model** | All 28 ratios | Learned | 8-quarter sequence | Does the *feature set* need expanding? |

- **A → B** measures coefficient drift.
- **B → C** measures the value of temporal structure.
- **C → D** measures the value of a richer feature set.

Each gap is a separate, attributable finding. "Our model got 0.88 AUC" is not publishable in 2026. "We decompose the failure of the field-standard formula into three attributable causes, and show that X accounts for most of it" is.

### Doing the Altman comparison rigorously

Three things are non-negotiable for reviewers:

**Use the right variant.** The original Z (1968) requires market value of equity and is calibrated for public manufacturing firms. For a mixed non-financial sample use **Z″** (non-manufacturing / emerging-market version). Running Z on retailers and getting bad results is a strawman a reviewer will catch.

**Report it two ways.** As a raw score ranked into an AUC (threshold-free and fair to Altman), *and* at its canonical cutoffs — 1.81 / 2.99 for Z — which is how it is actually used. Reporting only the second looks rigged.

**Don't stop at Altman.** Add **Ohlson's O-score** (1980, logit) and **Zmijewski's score** (1984, probit). Both are cheap to compute from data you already have. That converts "we beat one old formula" into "we benchmark against the classical scoring family."

---

## 5. Feature Set — All 28 Ratios

### Liquidity — 4

| # | Ratio | Formula |
|---|---|---|
| 1 | Current Ratio | Current Assets / Current Liabilities |
| 2 | Quick Ratio | (Current Assets − Inventory) / Current Liabilities |
| 3 | Cash Ratio | Cash & Equivalents / Current Liabilities |
| 4 | Working Capital to Total Assets **[Altman X₁]** | (Current Assets − Current Liabilities) / Total Assets |

### Profitability — 6

| # | Ratio | Formula |
|---|---|---|
| 5 | Net Profit Margin | Net Income / Revenue |
| 6 | Return on Assets (ROA) | Net Income / Total Assets |
| 7 | Return on Equity (ROE) | Net Income / Total Equity |
| 8 | EBITDA Margin | EBITDA / Revenue |
| 9 | EBIT to Total Assets **[Altman X₃]** | EBIT / Total Assets |
| 10 | Retained Earnings to Total Assets **[Altman X₂]** | Retained Earnings / Total Assets |

### Leverage — 5

| # | Ratio | Formula |
|---|---|---|
| 11 | Debt-to-Equity | Total Debt / Total Equity |
| 12 | Debt-to-Assets | Total Debt / Total Assets |
| 13 | Interest Coverage | EBIT / Interest Expense |
| 14 | Equity to Total Liabilities **[Altman X₄]** | Total Equity / Total Liabilities |
| 15 | Long-Term Debt to Total Assets | Long-Term Debt / Total Assets |

### Efficiency — 5

| # | Ratio | Formula |
|---|---|---|
| 16 | Asset Turnover **[Altman X₅]** | Revenue / Total Assets |
| 17 | Inventory Turnover | COGS / Inventory |
| 18 | Receivables Turnover | Revenue / Accounts Receivable |
| 19 | Payables Turnover | COGS / Accounts Payable |
| 20 | Cash Conversion Cycle (days) | DIO + DSO − DPO |

### Growth — 4

| # | Ratio | Formula |
|---|---|---|
| 21 | Revenue Growth (YoY) | (Revₜ − Revₜ₋₄) / \|Revₜ₋₄\| |
| 22 | Net Income Growth (YoY) | (NIₜ − NIₜ₋₄) / \|NIₜ₋₄\| |
| 23 | Total Assets Growth (YoY) | (TAₜ − TAₜ₋₄) / TAₜ₋₄ |
| 24 | Equity Growth (YoY) | (Eqₜ − Eqₜ₋₄) / \|Eqₜ₋₄\| |

### Cash Flow — 4

| # | Ratio | Formula |
|---|---|---|
| 25 | Operating Cash Flow to Current Liabilities | OCF / Current Liabilities |
| 26 | Free Cash Flow to Total Assets | (OCF − CapEx) / Total Assets |
| 27 | Accrual Quality | OCF / Net Income |
| 28 | Operating Cash Flow to Total Debt | OCF / Total Debt |

### XBRL tags required

`Assets` · `AssetsCurrent` · `Liabilities` · `LiabilitiesCurrent` · `StockholdersEquity` · `RetainedEarningsAccumulatedDeficit` · `CashAndCashEquivalentsAtCarryingValue` · `InventoryNet` · `AccountsReceivableNetCurrent` · `AccountsPayableCurrent` · `Revenues` (fallback `RevenueFromContractWithCustomerExcludingAssessedTax`) · `CostOfGoodsAndServicesSold` (fallback `CostOfRevenue`) · `OperatingIncomeLoss` · `NetIncomeLoss` · `InterestExpense` · `IncomeTaxExpenseBenefit` · `DepreciationDepletionAndAmortization` · `NetCashProvidedByUsedInOperatingActivities` · `PaymentsToAcquirePropertyPlantAndEquipment` · `LongTermDebtNoncurrent` · `LongTermDebtCurrent` · `ShortTermBorrowings`

**Derived quantities:**

- EBIT = `OperatingIncomeLoss`, or `NetIncomeLoss` + `InterestExpense` + `IncomeTaxExpenseBenefit`
- EBITDA = EBIT + `DepreciationDepletionAndAmortization`
- Total Debt = short-term borrowings + current LTD + non-current LTD — **not** total liabilities

### Four implementation gotchas

**Total Debt ≠ Total Liabilities.** Ratios 11, 12, 15 and 28 use interest-bearing debt only; ratio 14 uses total liabilities because that is what Altman specified. Mixing these up is the most common error in reproductions of Z-score studies.

**10-Q flow items are year-to-date, not quarterly.** Revenue, net income, OCF and CapEx in Q2/Q3 filings are cumulative from fiscal year start. Difference consecutive filings to recover discrete quarterly flows; Q4 must be backed out from the 10-K minus the first three quarters. Get this wrong and every flow-based ratio (5, 8, 16–19, 21, 22, 25–28) is corrupted.

**Growth is year-over-year, not quarter-over-quarter.** Comparing Q4 to Q3 confounds deterioration with seasonality. Hence t−4 in ratios 21–24.

**Negative equity and near-zero denominators.** ROE, D/E and Equity/Liabilities explode when equity goes negative — which is itself a distress signal, so don't just drop those rows. Either winsorise at the 1st/99th percentile, or add a binary `negative_equity` flag as a 29th feature and cap the ratio. The flag is preferable: it converts a data problem into a genuine predictor.

### Altman mapping

Model C uses exactly features **4, 10, 9, 14, 16** — X₁ through X₅ of the Z″ variant. Same five inputs as Models A and B, so the only thing changing across A → B → C is coefficients, then temporal structure. That is what makes each gap attributable.

X₄ here is the **book-value** form (Equity / Total Liabilities), used by Z′ and Z″. The original 1968 Z uses *market* value of equity, which would require price data from Yahoo Finance and market cap as an additional feature.

---

## 6. Architecture and Implementation Spec

| Component | Specification |
|---|---|
| **Dataset** | US listed non-financial firms (SIC 6000–6799 excluded), SEC EDGAR XBRL company-facts API, 2010–2024; UCI Taiwanese and Polish sets for external validation |
| **Features** | 28 ratios per firm-quarter across six families |
| **Sequences** | 8-quarter sliding window, stride 1; prediction horizons of 1, 2 and 4 quarters |
| **Split** | Chronological — train ≤2019, validation 2020–2021, test 2022–2024; scaler fitted on training partition only |
| **Deep models** | LSTM · Bi-LSTM · Transformer encoder · CNN-LSTM-Attention |
| **Classical baselines** | Altman Z″ · Ohlson O-score · Zmijewski · logistic regression · SVM · Random Forest · XGBoost · stacking ensemble |
| **Imbalance** | Class weights · SMOTE · Focal Loss (γ=2, α=0.25) · cost-sensitive threshold — compared as a full ablation |
| **Interpretability** | Attention weights over quarters, cross-checked against SHAP group importance over the six ratio families |
| **Evaluation** | ROC-AUC (primary) · PR-AUC · F1 · recall · specificity · cost-weighted loss · DeLong test for AUC comparison · McNemar's test · rolling-origin cross-validation |

### Model definitions

**LSTM (baseline)**
`LSTM(64, return_sequences=True)` → `LSTM(32)` → `Dense(16, ReLU)` → `Dropout(0.3)` → `Dense(1, sigmoid)`
Adam, lr 1e-3, batch 32, EarlyStopping on validation AUC, patience 10.

**Bi-LSTM**
`BiLSTM(64)` → `Dense(32, ReLU)` → `Dropout(0.3)` → `Dense(1, sigmoid)`

**Transformer encoder (primary)**
Linear embedding to 64 dims → sinusoidal positional encoding → 2 encoder blocks, 8 heads each, 128-unit FFN, layer norm + residual → `GlobalAveragePooling1D` → `Dense(32)` → `Dense(1, sigmoid)`

**CNN-LSTM-Attention (hybrid)**
`Conv1D(32, kernel=3, ReLU)` → `MaxPooling1D(2)` → `LSTM(64, return_sequences=True)` → additive attention → `Dense(16)` → `Dropout(0.3)` → `Dense(1, sigmoid)`

All four share the same input tensor (8 quarters × 28 ratios), split, imbalance treatment and tuning budget, so differences are attributable to architecture alone.

### Expanded scope drawn from the literature

| Addition | Source |
|---|---|
| Focal Loss + cost-sensitive threshold | Chang, Liu & Deng 2025 |
| Information Gain + PSO hybrid feature selection | Chen, Liu & Wu 2025 |
| Shapley group importance alongside attention | Korangi et al. 2023 |
| Multi-horizon term-structure output head | Korangi et al. 2023 |
| Socio-economic cost evaluation | Radovanovic & Haas 2023 |
| Market/pricing, text and ESG channels | Korangi 2023; Chen 2023; Chang 2025 |
| Graph + LLM fusion — **future work only** | Xiong et al. 2026; He 2025 |

**Priority given the fixed schedule:**

| Tier | Additions |
|---|---|
| Must-do | Broader baselines table, socio-economic cost metrics, Shapley + attention dual interpretability |
| Should-do if time allows | Hybrid feature selection, broader imbalance toolkit, multi-horizon output |
| Nice-to-have | Text/ESG input channels, multi-class distress extension |
| Future-work only | Graph + LLM fusion |

---

## 7. Contributions and Target Venues

### Contributions to claim

1. A **temporal panel dataset** of US listed non-financial firms built from free sources and released publicly — addressing the cross-sectional monoculture of the UCI datasets used by 7 of the 21 reviewed papers.
2. The **first head-to-head comparison** of four temporal architectures under one dataset, split, imbalance treatment and tuning budget.
3. A **decomposition of classical-formula failure** into coefficient drift, static formulation and feature-set limitation.
4. **Period-level interpretability** — identifying which quarters carry the warning signal, validated by two independent methods.
5. A **methodological audit** showing that reported accuracies of 91–99% arise from balanced samples, random splits and accuracy-on-imbalanced-data, and demonstrating what survives a chronological split at realistic base rates.

Contribution 5 is the one reviewers will remember, and it requires the least extra work — it comes free from re-running the standard baselines correctly.

### Candidate titles

- *Does Time Matter? A Temporal Deep Learning Benchmark for Corporate Bankruptcy Prediction*
- *Beyond the Z-Score: Decomposing the Failure of Static Bankruptcy Formulas with Sequence Models*
- *Revisiting Bankruptcy Prediction: Chronological Evaluation of Temporal Deep Learning against Classical Scoring*

### Target venues

**Expert Systems with Applications** or **IEEE Access** for the full study; **IEEE Transactions on Computational Social Systems** if the methodological-audit angle leads. Conference fallback: ICERCS, ISCBI, ICAICCIT — but these are where the inflated-accuracy papers live, so a journal is the better home for a paper criticising that practice.

---

## 8. Presentation — Structure, Splits, Script

**File:** `Capstone_Title_Approval_Bankruptcy_Prediction.pptx` — 18 slides on the MPSTME template.

### Slide structure

| # | Slide | # | Slide |
|---|---|---|---|
| 1 | Title slide | 10 | Feasibility: Financial and Risk |
| 2 | Introduction | 11 | Technology Stack |
| 3 | Problem Statement | 12 | Proposed Architecture and Pipeline |
| 4 | Aim and Objectives | 13 | Algorithms and Model Progression |
| 5 | Literature Review (1 of 2) | 14 | Evaluation Protocol and Enhancements |
| 6 | Literature Review (2 of 2) | 15 | Timeline: 14-Week Plan |
| 7 | Research Gap | 16 | Conclusion |
| 8 | Scope | 17 | References (1 of 2) |
| 9 | Feasibility: Technical and Data | 18 | References (2 of 2) |

### Presenter split

| Presenter | Slides | Section | Est. time |
|---|---|---|---|
| **Manognaa Vakkalanka** | 1–4 | Title & team intro, Introduction, Problem Statement, Aim & Objectives | ~3:20 |
| **Harshit Bhinde** | 5–8 | Literature Review (both tables), Research Gap, Scope | ~3:55 |
| **Aakaash D Limaye** | 9–12 | Feasibility ×2, Technology Stack, Proposed Architecture | ~3:40 |
| **PV Krishna Teja** | 13–18 | Algorithms, Evaluation, Timeline, Conclusion, References | ~3:45 |

Total ≈ 14:40 including handovers.

### Handover cues

- **Manognaa → Harshit** (after Slide 4): "…and to establish that this gap is real, we reviewed ten recent papers."
- **Harshit → Aakaash** (after Slide 8): "…having defined what we will and won't cover, over to the question of whether it's actually buildable."
- **Aakaash → Teja** (after Slide 12): "…that's the pipeline — Teja will take you through the models themselves."

### Viva question ownership

Manognaa — motivation and scope. Harshit — literature and novelty (*"how is this different from paper 2?"* is the most likely challenge). Aakaash — data availability and feasibility. Teja — architecture choices and evaluation.

### If running long

Cut Slide 11 (Technology Stack — the panel can read it) and compress Slide 6 to "the remaining five papers show the same pattern."

### Script — Harshit's section (Slides 5–8), ~4 minutes

**Slide 5 — Literature Review (1 of 2) · ~1:05**

> Thanks, Manognaa.
>
> We reviewed ten papers published between 2022 and 2026, all Scopus-indexed — mostly *Expert Systems with Applications* and the *European Journal of Operational Research*.
>
> Rather than walk through every row, let me pull out three from this first set.
>
> Sigrist and Leuenberger combine tree-boosting with a frailty model to predict default over multiple periods. Strong results — but look at their limitation: every predictor is taken at a single point in time. They themselves say adding lagged information is future work.
>
> Row two is the paper closest to what we're proposing. Korangi, Mues and Bravo apply a transformer to panel data and get a sizeable AUC improvement over traditional models. That's the strongest existing evidence that our direction works.
>
> And Radovanovic and Haas make a point we've adopted directly — that models should be judged on economic cost, not accuracy alone.

**Slide 6 — Literature Review (2 of 2) · ~1:05**

> The second set shows where the field's energy has actually gone — and it isn't sequence modelling.
>
> Papers six and seven are both stacking ensembles. Chen, Liu and Wu add hybrid feature selection; Chang, Liu and Deng add ESG scores and Focal Loss for imbalance. Both are strong tabular models, and we've borrowed their imbalance techniques — but neither treats time as a dimension.
>
> Paper eight is worth flagging. Sun calls it a deep learning model, and it is a five-layer network — but it consumes a single period of twenty-three indicators. Depth without sequence. It reports 78% accuracy, which sits squarely in the traditional range.
>
> Paper ten is the newest, from *Information Sciences* this year. Xiong and colleagues use a large language model to build a company relationship graph. Genuinely novel — and we've recorded it as future work rather than scope, because it needs data we don't have.

**Slide 7 — Research Gap · ~0:55** *(slow down — this is the payoff)*

> So this is the gap.
>
> On the left, four things the literature has settled. Machine learning beats linear scoring. Imbalance handling materially changes results. Evaluation should reflect economic cost. And deep models do win when you give them true panel data.
>
> On the right is what's still open — and this is the core of our case.
>
> Most models still consume a single snapshot. Sequence models are rare: across ten papers there is exactly one transformer study, and no LSTM comparison at all. Which quarters actually signal failure is essentially unanswered.
>
> And critically — nobody has compared these architectures against each other on one dataset, under one protocol. *[pause]* That is what we're proposing to do.

**Slide 8 — Scope · ~0:50**

> Briefly, what that means in practice.
>
> In scope: publicly listed non-financial US companies, quarterly data from roughly 2010 to 2024, twenty-five to thirty standard ratios, and a look-back window of eight to ten quarters. Four deep architectures, benchmarked against five classical models, with attention and Shapley for interpretation.
>
> Just as important is what we're excluding. No private or financial-sector firms. No production deployment. No paid data — everything comes from SEC EDGAR, Kaggle and Yahoo Finance. No trading strategy. And the graph and LLM work I mentioned stays as future work.
>
> We've drawn those boundaries deliberately, so the comparison stays clean and the timeline stays realistic.
>
> Aakaash will now take you through whether this is actually buildable.

**Pacing:** ~620 words, about 4:05 at normal speaking rate. To claw back time, cut the Chang/ESG sentence on slide 6 and the "no trading strategy" line on slide 8.

**Expected questions:**

- *"How is yours different from the Korangi transformer paper?"* — they do term-structure prediction on mid-caps with market data; we compare four architectures head-to-head on ratio sequences with period-level attention.
- *"Why not just use the newest LLM-graph method?"* — it requires relational and multi-modal data we can't source for free, and the comparison we're running has to be clean.

---

## 9. In-Depth Explanation of Slides 5–8

### Slide 5 — Literature Review (1 of 2)

#### Paper 1 — Sigrist & Leuenberger (2023), EJOR

Predicted the probability that a company defaults over several future horizons, using a hybrid of machine learning and classical econometrics.

- **Default** — failure to meet a debt obligation. Broader than bankruptcy: a firm can default without filing.
- **Tree-boosting (gradient boosting)** — build many small decision trees *sequentially*. Tree 1 makes a rough prediction; tree 2 predicts tree 1's errors; tree 3 predicts the remaining error. The sum is the final model. XGBoost and LightGBM belong to this family — currently the strongest general-purpose method for tabular data.
- **Frailty** — borrowed from survival analysis. An *unobserved* random variable making some entities more failure-prone than measured characteristics suggest. In credit risk it captures common shocks — a recession hits every firm at once, so defaults cluster in time in a way no firm-level ratio explains. A **latent frailty model** estimates that hidden shared factor.
- **LaGaBoost** — their hybrid: Latent Gaussian (frailty) + Boosting (trees).
- **Cumulative vs forward probabilities** — *cumulative* = probability of defaulting at any point within N years. *Forward* = probability of defaulting in year N specifically, given survival to year N−1.
- **Tail probabilities** — the extreme-loss end of the portfolio loss distribution. Banks care because capital requirements are set against worst-case, not average, losses.

**Why it's on the slide:** every predictor is measured at one point in time. Their own conclusion says including *lagged* information (values from t−1, t−2, …) is future work. That sentence is, almost literally, the opening for this project.

#### Paper 2 — Korangi, Mues & Bravo (2023), EJOR

**The single most important paper.** Applies a Transformer to corporate default prediction.

- **Mid-cap** — publicly traded companies under US$10bn market capitalisation. They default more often than large caps and have patchier data, so they're harder and more interesting.
- **Panel data** — observations of the *same entities repeatedly over time*; a grid of firms × quarters. Contrast **cross-sectional** (many firms, one moment) and **time series** (one entity, many moments). Panel data is what makes sequence modelling possible; almost every other paper flattens it into cross-sections first.
- **Transformer** — a network built on **self-attention**. For each element in a sequence, the model computes a weighted average of *all* elements, weights learned. Quarter 7 can directly "look at" quarter 2 in one step. An LSTM must pass information through every intervening quarter, which degrades it.
- **Multi-head attention** — several attention mechanisms in parallel, each free to learn a different relationship (one head might track leverage trends, another liquidity).
- **Positional encoding** — self-attention has no built-in notion of order, so you explicitly add a signal encoding each position's index. Without it the model can't tell Q1 from Q8.
- **Multi-label classification** — each sample carries a *vector* of binary labels rather than one: defaults within 3 months? 6? 1 year? 3? That vector is the **term structure** of default probability.
- **Multi-channel architecture** — separate sub-networks for separate data types (accounting fundamentals, market data, daily prices), fused later. Needed because those sources arrive at very different frequencies.
- **Shapley values** — from cooperative game theory. If features are "players" cooperating to produce a prediction, the Shapley value is the fair share of the payout attributable to each, averaged over all possible coalitions. **SHAP** is the standard implementation. They compute it over *groups* of features (whole data channels).
- **AUC (ROC-AUC)** — the probability that the model assigns a higher risk score to a randomly chosen bankrupt firm than to a randomly chosen healthy one. 0.5 = coin flip, 1.0 = perfect. Standard under imbalance because it's rank-based and threshold-free — it can't be gamed by predicting "healthy" for everyone.

**Why it's on the slide:** proof the direction works, *and* the likely novelty challenge. Differentiator: they do term-structure prediction on mid-cap multi-source data; you compare four temporal architectures head-to-head on ratio sequences with period-level attention analysis.

#### Paper 3 — Radovanovic & Haas (2023), ESWA

Argued the field measures the wrong thing, and re-ran standard models under cost-based metrics.

- **Multivariate Discriminant Analysis (MDA)** — the classical technique Altman used in 1968. Finds the linear combination of variables that maximally separates two groups.
- **Type I / Type II error** — a **false positive** flags a healthy firm as failing (denying a good loan — opportunity cost); a **false negative** misses a firm that actually fails (lending and losing principal — usually far more expensive). Which one is called "Type I" flips depending on which class is labelled positive, so in the viva describe them as false positive/false negative rather than by number.
- **Balanced accuracy (BACC)** — average of sensitivity and specificity. Used because with 2% bankruptcies, predicting "healthy" always scores 98% accuracy while being useless.
- **Finding:** two models can differ trivially on AUC yet differ enormously in money lost and jobs lost. The "best" model depends entirely on which metric you optimise.

#### Paper 4 — Chen, Liao, Chen, Kang & Lin (2023), ESWA

Added information from the *narrative text* of annual reports to standard ratio models.

- **Text-based communicative value** — their measure of how much genuine information the prose conveys, as distinct from word-frequency counts or sentiment polarity. Intuition: firms in trouble write more obscurely.
- **EasyEnsemble** — randomly undersample the majority class k times to build k balanced datasets, train a model on each, combine. Keeps all minority examples without permanently discarding majority information.
- **BalancedBaggingClassifier** — bagging where each bootstrap sample is resampled to be class-balanced.
- **Scale:** 40,507 non-bankrupt vs 932 bankrupt observations — a 2.2% positive rate. Quote this if anyone doubts imbalance is a real problem.

#### Paper 5 — Chakroun, Abid, Elarbi & Masmoudi (2024), ESWA

Modelled *when* a firm defaults, not just whether — using statistics rather than ML.

- **Survival analysis** — statistics for time-until-event data. Originally medical (time until death), now standard in credit risk.
- **Censoring** — the defining problem it solves. At the end of your window most firms haven't defaulted. You don't know they never will; only that they hadn't *yet*. Ordinary regression discards that; survival models use it.
- **Hazard** — the instantaneous rate of the event at time t, given survival up to t.
- **Cox proportional hazards** — the standard semi-parametric model. Covariates multiply a shared **baseline hazard** whose shape you never specify.
- **Mixture cure model** — assumes part of the population will *never* experience the event ("cured"). Splits into **incidence** (will this firm ever default?) and **latency** (given that it will, when?). Sensible for firms, since most healthy companies never default.
- **Gamma-Lindley distribution** — a parametric distribution for the latency part, chosen for flexibility fitting skewed waiting times.
- **Parametric vs non-parametric** — parametric assumes a specific distributional form with fixed parameters. More efficient if right, badly wrong if not.
- **K-means** — partition observations into k groups by nearest centroid, iterated until stable. Used to group firms into short-, medium- and long-term risk classes.

**Why it's on the slide:** the methodological opposite of your approach — fully interpretable, assumption-heavy, no learned representations. Marks one end of the interpretability/flexibility trade-off you sit in the middle of.

### Slide 6 — Literature Review (2 of 2)

#### Paper 6 — Chen, Liu & Wu (2025), ESWA

- **Multi-class financial distress prediction (FDP)** — several graded states of distress instead of binary. Harder, more operationally useful.
- **Information Gain (IG)** — a filter feature-selection score measuring how much the **entropy** (uncertainty) of the target drops once you know a feature's value. Weakness they acknowledge: it captures mainly *linear/marginal* association and can discard features that matter only in nonlinear combination.
- **Particle Swarm Optimisation (PSO)** — population-based search. Candidate solutions ("particles") fly through the search space, pulled toward their own best position and the swarm's best. Used to search feature subsets, a space too large to enumerate.
- **Genetic Algorithm (GA)** — evolutionary search: maintain a population, select the fittest, recombine (**crossover**), randomly perturb (**mutation**), repeat.
- **Stacking ensemble** — train several diverse **base learners**, then train a **meta-learner** on their predictions. The meta-learner learns *when to trust which base model*.
- **Hyperopt** — Bayesian hyperparameter optimisation. Builds a probabilistic model of which hyperparameters score well and samples where improvement is likely.

#### Paper 7 — Chang, Liu & Deng (2025), Applied Soft Computing

- **ESG** — Environmental, Social and Governance ratings. Their contribution: showing these carry default-relevant signal beyond financials.
- **A-share** — shares of mainland Chinese companies on the Shanghai/Shenzhen exchanges, denominated in RMB. (**ST** — *Special Treatment*, a flag Chinese exchanges apply to financially abnormal firms; the standard distress label in Chinese studies.)
- **Cross-entropy loss** — the default classification loss: −log(probability assigned to the true class). Punishes confident wrong answers heavily.
- **Focal Loss** — multiplies each example's loss by (1 − p)^γ, where p is the predicted probability of the correct class. Easy, well-classified examples get their loss crushed toward zero, concentrating gradient updates on hard and rare cases. From object detection (RetinaNet), where background pixels overwhelm objects — structurally the same problem as 98% healthy firms. **The single most transferable technique in the review.**
- **Cost-sensitive decision threshold** — choose the cut-off that minimises *expected cost*, given a missed bankruptcy costs far more than a false alarm. Free accuracy-for-money trade without retraining.

#### Paper 8 — Sun (2024), Procedia Computer Science

- **Feedforward network / MLP** — fully connected layers, information flows one way, no memory of previous inputs. Architecture: 23→18→14→10→5→2.
- **BP algorithm** — backpropagation, computing gradients by the chain rule backwards through the network.
- **Why flag it:** it is genuinely deep — five layers — but consumes a **single period** of 23 indicators. Depth is not sequence modelling. Reports 78% accuracy, right in the traditional band. The cleanest illustration that "deep learning has already been tried" is not a valid objection.

#### Paper 9 — Förch Brenes, Johannssen & Chukhrova (2022), ISWA

- An MLP with a systematic sweep over optimisers, activation functions, layer counts and neuron counts.
- **Activation function** — the nonlinearity at each neuron (ReLU, sigmoid, tanh). Without one, stacked layers collapse mathematically into a single linear layer.
- **Optimiser** — the algorithm updating weights from gradients (SGD, Adam, RMSprop).
- **Real value:** contains a literature review covering 500+ bankruptcy studies since the 1930s. Cite it for the historical arc (Beaver 1966 → Altman 1968 → logit 1980s → ANN/SVM 1990s–2000s → ensembles 2010s) instead of reading fifty papers.

#### Paper 10 — Xiong et al. (2026), Information Sciences

- **Multi-modal** — combining fundamentally different data types (numeric financials, natural-language disclosures, graph structure).
- **Graph** — nodes (companies) connected by edges (supply chain, shared ownership, sector). **Edge weight** = strength of connection.
- **Graph Convolutional Network (GCN)** — updates each node's representation by aggregating its neighbours'. Distress propagates across the graph as it does in reality — a supplier's collapse damages its customers.
- **Their LLM trick:** use a large language model to *read* financial indicators, risk events and news, and infer how strongly two companies' risks are linked — turning unstructured text into numeric edge weights.
- **Over-smoothing** — the characteristic failure of deep GNNs. Repeated neighbour-averaging makes every node's representation converge, erasing the differences you needed. Their **high-frequency graph convolution** amplifies the *difference* between a node and its neighbours rather than averaging it away.
- **Cross-modal vs intra-modal attention** — attention *between* data types (does the text corroborate the numbers?) versus *within* one type.

**Why future work, not scope:** needs an inter-firm relationship graph and curated news, neither sourceable free for a US listed universe in 14 weeks.

### Slide 7 — Research Gap

See [Section 3](#3-the-research-gap) above for the full treatment.

### Slide 8 — Scope

#### In scope, and the reasoning

- **Publicly listed non-financial companies.** Listed because they must file standardised statements. **Non-financial** because banks and insurers have structurally different balance sheets — high leverage is their business model, not a warning sign — so debt-to-equity isn't comparable across the boundary. Standard practice, not a shortcut.
- **SEC EDGAR** — Electronic Data Gathering, Analysis and Retrieval, the SEC's public filing repository. **10-K** = annual, **10-Q** = quarterly. Filings are tagged in **XBRL**, letting you pull "Total Current Liabilities" programmatically instead of parsing PDFs.
- **28 ratios across six families** — liquidity (can it pay short-term bills), profitability (does it earn), leverage (how much debt), efficiency (how hard assets work), growth (direction of travel), cash flow (does profit convert to cash). Six families because deterioration surfaces in different ones at different stages: profitability weakens first, liquidity later, and by the time leverage looks alarming it's usually too late.
- **Look-back window of 8 quarters** — how much history each sample contains. **Prediction horizon of 1–4 quarters** — how far ahead you forecast. Two independent knobs, frequently confused. Samples come from a **sliding window**: quarters 1–8 predict 9, then 2–9 predict 10, multiplying usable samples from a limited number of firms.
- **Attention weights and Shapley group importance** — two *independent* interpretability methods. Attention comes free from the model's internals; Shapley is computed externally by perturbing inputs. Reporting both matters because attention weights are contested in the ML literature as a faithful explanation — if the two agree, the interpretation is far more defensible.

#### Out of scope, and why each exclusion is defensible

- **Private and financial-sector firms** — no mandatory standardised filings, and non-comparable ratios respectively.
- **Production deployment / API / dashboards** — engineering work consuming weeks, demonstrating nothing about the research question.
- **Compustat, CRSP, Bloomberg** — the paid databases most of these papers use. **Compustat** (S&P) is standardised fundamentals; **CRSP** (Chicago) is historical securities prices. Excluding them costs some data quality and buys total reproducibility — a genuine selling point for a publication.
- **Trading strategy or portfolio construction** — a different discipline requiring backtesting infrastructure and transaction-cost modelling.
- **Graph/LLM fusion** — paper 10's approach; needs relational data you can't source.
- **Cross-country generalisation** — training on US and testing on Taiwan/Poland adds an accounting-standards confound (US GAAP vs IFRS vs local standards means "total assets" isn't the same quantity), so it stays exploratory rather than a claim.

**Framing if challenged:** every exclusion protects either the cleanliness of the comparison or the realism of the timeline. Much stronger than "we didn't have time."

---

## 10. Logbook Entries — 7 Fortnights

**Format fields per entry:** Week No, Date of Reporting, From/To dates, Work carried out. Faculty Remark and Faculty Signature remain blank for Prof. Deepali Maste.

**TITLE OF THE PROJECT:** Bankruptcy Prediction using Temporal Deep Learning: A Comparative Study of LSTM and Transformer Models

**Dates assume Week 1 began Monday 10/08/2026.** Topic finalisation and feasibility analysis were completed before the logbook period and are not recorded here.

### Week No: 1–2 | Date of Reporting: 24/08/2026
**From 10/08/2026 to 23/08/2026**

Conducted a systematic literature review of ten Scopus-indexed papers published between 2022 and 2026. Sources included Korangi, Mues and Bravo (EJOR 308) on transformer-based default prediction; Sigrist and Leuenberger (EJOR 305) on tree-boosting with latent frailty; Radovanovic and Haas (ESWA 227) on socio-economic cost metrics; Chen et al. (ESWA 233) on text-augmented models; Chakroun et al. (ESWA 257) on the Gamma-Lindley cure model; Chen, Liu and Wu (ESWA 282) and Chang, Liu and Deng (ASOC 171) on stacking ensembles; Sun (Procedia CS 243) and Förch Brenes et al. (ISWA 16) on feedforward networks; and Xiong et al. (Information Sciences 744) on LLM-driven multi-modal graph models. Prepared a literature matrix recording technique, dataset, limitations and stated future work for each. Established the research gap: of ten papers only one applies a sequence model, none benchmark LSTM against Transformer, and no study compares architectures under a single shared dataset and protocol. Prepared and delivered the 18-slide title approval presentation with responsibilities divided across all four members. Initiated dataset collection against the SEC EDGAR XBRL company-facts API (`data.sec.gov/api/xbrl/companyfacts/`), retrieving 10-K and 10-Q filings for US listed firms from 2010 onward, and downloaded the Taiwanese Bankruptcy Prediction dataset (6,819 firms, 95 features) and the Polish companies bankruptcy dataset from the UCI repository as supplementary labelled sources. Filtered out SIC codes 6000–6799 to exclude banking, insurance and real estate firms, whose balance sheet structure makes leverage ratios non-comparable. Finalised the feature set of 28 financial ratios across six families — liquidity, profitability, leverage, efficiency, growth and cash flow — selected by cross-referencing the variables used across the reviewed papers, and mapped each to its underlying us-gaap taxonomy tags including Assets, AssetsCurrent, LiabilitiesCurrent, StockholdersEquity, Revenues, NetIncomeLoss, InventoryNet and InterestExpense.

### Week No: 3–4 | Date of Reporting: 07/09/2026
**From 24/08/2026 to 06/09/2026**

Built the ratio computation pipeline implementing all 28 selected features: liquidity (current, quick, cash, working capital to total assets), profitability (net margin, ROA, ROE, EBITDA margin), leverage (debt-to-equity, debt-to-assets, interest coverage, debt service coverage), efficiency (asset turnover, inventory turnover, receivables turnover, days sales outstanding), growth (year-on-year revenue, profit, asset and equity growth) and cash flow (operating cash flow to current liabilities, free cash flow, cash flow to net income). Cross-verified bankruptcy events against SEC Form 8-K Item 1.03 filings and public bankruptcy court records to fix the exact event date for labelling. Applied forward fill within a firm for short gaps and winsorised at the 1st and 99th percentiles to control division-driven outliers arising from near-zero denominators. Completed exploratory data analysis covering class distribution, feature correlation and distributional differences between failing and surviving firms, confirming a positive class rate of approximately 3% consistent with the reviewed literature. Difficulty faced: inconsistent XBRL tag usage across filers required a fallback tag-mapping dictionary, and roughly 12% of firm-quarters lacked complete cash flow statement items.

### Week No: 5–6 | Date of Reporting: 21/09/2026
**From 07/09/2026 to 20/09/2026**

Constructed temporal sequences using a sliding window of eight quarters with stride one and prediction horizons of one to four quarters ahead. Implemented a strictly chronological partition — training on filings up to 2019, validation on 2020–2021 and testing on 2022–2024 — so that no future information reaches the training set. Fitted StandardScaler on the training partition only and applied the stored parameters to validation and test data to prevent leakage. Implemented the baseline LSTM in Keras: LSTM(64, return_sequences=True), LSTM(32), Dense(16, ReLU), Dropout(0.3), Dense(1, sigmoid), trained with Adam at learning rate 1e-3, batch size 32, and EarlyStopping on validation AUC with patience 10. Applied class weighting and SMOTE from imbalanced-learn, resampling only within the training fold. Recorded ROC-AUC, PR-AUC, F1, precision, recall and specificity. Difficulty faced: the baseline initially overfitted within eight epochs, addressed by raising dropout and adding L2 regularisation.

### Week No: 7–8 | Date of Reporting: 05/10/2026
**From 21/09/2026 to 04/10/2026**

Implemented the Bidirectional LSTM variant with BiLSTM(64), Dense(32), Dropout(0.3) and sigmoid output to evaluate the contribution of bidirectional context across the look-back window. Implemented the Transformer encoder: a Dense linear embedding to 64 dimensions, sinusoidal positional encoding to preserve quarter ordering, two encoder blocks each with eight-head self-attention, a 128-unit feed-forward sub-layer, layer normalisation and residual connections, followed by GlobalAveragePooling1D, Dense(32) and a sigmoid output. Tuned both architectures under a tuning budget identical to the baseline so the comparison remains fair. Extracted and stored per-head attention weight matrices for later interpretation. Recorded the same metric set as the baseline for direct comparison. Difficulty faced: the Transformer overfitted given the limited positive class and required capacity reduction from four encoder blocks to two, along with increased dropout in the feed-forward sub-layer.

### Week No: 9–10 | Date of Reporting: 19/10/2026
**From 05/10/2026 to 18/10/2026**

Implemented the CNN-LSTM-Attention hybrid: Conv1D(32, kernel size 3, ReLU), MaxPooling1D(2), LSTM(64, return_sequences=True), an additive attention layer, Dense(16), Dropout(0.3) and sigmoid output, combining local pattern extraction with sequence modelling. Implemented Focal Loss with gamma 2.0 and alpha 0.25 following Chang, Liu and Deng, and a cost-sensitive decision threshold replacing the default 0.5 cut-off. Ran a controlled comparison of four imbalance strategies — class weighting, SMOTE, Focal Loss and threshold tuning — across all four architectures under an identical tuning budget, producing a full ablation grid. Consolidated results into a single comparison table covering all architecture and imbalance-strategy combinations. Difficulty faced: the ablation grid required a large number of training runs, mitigated by checkpointing models and reducing redundant configurations after early results showed SMOTE underperforming Focal Loss on sequence inputs.

### Week No: 11–12 | Date of Reporting: 02/11/2026
**From 19/10/2026 to 01/11/2026**

Generated attention heat maps averaged separately over failing and surviving firms to identify which quarters within the eight-quarter window carried the highest predictive weight, replicating the analysis approach of Korangi et al. Computed SHAP group importance over the six ratio families as an independent interpretability check, since attention weights alone are contested as a faithful explanation of model behaviour. Implemented benchmark models under the identical dataset, split and metrics: Altman Z-score, logistic regression, RBF-kernel SVM, Random Forest, XGBoost and a stacking ensemble. Applied DeLong's test to compare AUC values pairwise and McNemar's test for classification agreement. Performed rolling-origin time-series cross-validation to confirm stability across periods. Evaluated all models on a cost-based metric weighting false negatives more heavily than false positives, following Radovanovic and Haas. Reported performance separately at one, two and four quarter horizons to establish how early the warning signal becomes reliable.

### Week No: 13–14 | Date of Reporting: 16/11/2026
**From 02/11/2026 to 15/11/2026**

Drafted the research paper covering problem formulation, related work, methodology, experimental design, results and comparative analysis, targeting a Scopus-indexed venue with Expert Systems with Applications as the primary submission target. Prepared the capstone project report in the prescribed institutional format, including literature review, system design, implementation, results, discussion and conclusion, with ROC curves, confusion matrices, attention heat maps and model comparison tables. Cleaned and documented the codebase, added a README specifying environment, data acquisition steps and reproduction instructions, and finalised the public GitHub repository so results can be independently reproduced from free data sources alone. Prepared the final presentation and live demonstration, conducted an internal review across all four members and incorporated mentor feedback. Difficulty faced: compressing the full four-architecture comparison within the target venue's page limit required moving ablation results to supplementary material.

**Note:** Weeks 1–2 is noticeably denser than the others. If the logbook box is small, the honest trim is to drop the us-gaap tag list, since that detail resurfaces in Weeks 3–4 anyway.

---

## 11. IEEE Search Keywords

IEEE Xplore indexes this topic under different vocabulary than Elsevier. "Bankruptcy prediction" alone returns thin results; the productive terms are **financial distress**, **credit risk**, **default prediction** and **financial early warning**.

### Keyword bank

**Problem terms:** `bankruptcy prediction` · `financial distress prediction` · `corporate default prediction` · `credit risk assessment` · `credit scoring` · `financial early warning` · `business failure prediction` · `loan default prediction` · `firm failure`

**Method terms:** `LSTM` · `long short-term memory` · `recurrent neural network` · `BiLSTM` · `GRU` · `transformer` · `self-attention` · `attention mechanism` · `temporal convolutional network` · `sequence model` · `time series classification` · `temporal deep learning`

**Data terms:** `financial ratios` · `financial statements` · `panel data` · `quarterly data` · `time series` · `sliding window`

**Supporting-technique terms:** `class imbalance` · `imbalanced data` · `SMOTE` · `focal loss` · `cost-sensitive learning` · `ensemble learning` · `stacking`

**Interpretability terms:** `explainable AI` · `XAI` · `interpretable machine learning` · `SHAP` · `attention weights` · `feature importance`

### Command-search strings

```
("All Metadata":"bankruptcy prediction") AND ("All Metadata":"deep learning")
("All Metadata":"financial distress prediction") AND ("All Metadata":"deep learning")
("All Metadata":"bankruptcy") AND ("All Metadata":"LSTM" OR "All Metadata":"recurrent neural network")
("All Metadata":"corporate default") AND ("All Metadata":"transformer")
("All Metadata":"financial distress") AND ("All Metadata":"time series") AND ("All Metadata":"classification")
("All Metadata":"credit risk") AND ("All Metadata":"temporal" OR "All Metadata":"sequential")
("All Metadata":"financial ratios") AND ("All Metadata":"sequence" OR "All Metadata":"LSTM")
("All Metadata":"bankruptcy") AND ("All Metadata":"attention mechanism")
("All Metadata":"self-attention") AND ("All Metadata":"credit risk")
("All Metadata":"temporal convolutional network") AND ("All Metadata":"default" OR "All Metadata":"distress")
("All Metadata":"class imbalance") AND ("All Metadata":"bankruptcy" OR "All Metadata":"credit")
("All Metadata":"focal loss") AND ("All Metadata":"credit" OR "All Metadata":"default")
("All Metadata":"explainable" OR "All Metadata":"interpretable") AND ("All Metadata":"credit risk")
("All Metadata":"SHAP") AND ("All Metadata":"default" OR "All Metadata":"credit")
```

### Two terminology notes that change yield

**"Financial early warning"** — heavily used by Chinese-affiliated authors in IEEE venues, often paired with **"ST company"**. A rich vein that "bankruptcy" searches miss entirely.

**Peer-to-peer lending default prediction** — a large IEEE literature using exactly these methods on a structurally identical problem. Methodologically citable even though the entity is a borrower rather than a firm.

### Filters and venues

Year range **2020–2026**, content type **Journals + Conferences**. Hits concentrate in **IEEE Access**, **IEEE Transactions on Computational Social Systems**, **IEEE Transactions on Neural Networks and Learning Systems**, and **IEEE TKDE**. On any good result, click through its **IEEE Terms** and **INSPEC Controlled Terms** to snowball — relevant controlled terms are `bankruptcy`, `financial data processing`, `risk management`, `recurrent neural nets`, `pattern classification`, `time series`.

**If results are thin, that's a finding.** Record the exact query and hit count: "a search of IEEE Xplore for temporal deep learning applied to bankruptcy prediction returned N results" is a citable sentence for the introduction.

---

## 12. Deliverables and Open Questions

### Files produced

| File | Description |
|---|---|
| `Capstone_Title_Approval_Bankruptcy_Prediction.pptx` | 18-slide title approval presentation on the MPSTME template |
| `Bankruptcy_Prediction_Concept.pdf` | Two-page A4 concept note with pipeline, architecture and decomposition diagrams |
| `Bankruptcy_Prediction_Concept.html` | HTML source of the above (delete if not needed) |
| `Capstone_Session_Notes.md` | This document |

### Open questions

1. **Which formula is "the 20-year formula"?** Altman Z-score is 1968 (58 years old), Ohlson O-score 1980, Zmijewski 1984. The concept note currently uses **Altman Z″** as the classical baseline. If a mentor or source named a different model, this needs changing — describing Altman as "20 years old" in a paper is an easy factual error for a reviewer to catch.
2. **Spec numbers are proposals, not confirmed decisions** — 28 ratios, 8-quarter window, train ≤2019 / val 2020–21 / test 2022–24. These appear in the diagrams and tables and would need regenerating if changed.
3. **Altman X₄ variant** — currently the book-value form (Equity / Total Liabilities) used by Z′ and Z″. The original 1968 Z uses *market* value of equity, requiring price data from Yahoo Finance and market cap as an extra feature.
4. **Negative-equity flag** — recommended as a 29th binary feature rather than dropping affected rows. Not yet decided.

### Outstanding tasks

- Fill the title slide with the four members' names, SAP IDs, roll numbers and Prof. Deepali Maste as guide.
- Slide 12's flow shows step 4 → 5 wrapping to the second row without an arrow between rows.
- Download the full PDF of Xiong et al. (2026) — only the abstract page is held.
- Produce the logbook as a filled Word/PDF document matching the uploaded layout, if required.

### Key references

1. Sigrist, F., & Leuenberger, N. (2023). Machine learning for corporate default risk: Multi-period prediction, frailty correlation, loan portfolios, and tail probabilities. *European Journal of Operational Research, 305*(3), 1390–1406.
2. Korangi, K., Mues, C., & Bravo, C. (2023). A transformer-based model for default prediction in mid-cap corporate markets. *European Journal of Operational Research, 308*(1), 306–320.
3. Radovanovic, J., & Haas, C. (2023). The evaluation of bankruptcy prediction models based on socio-economic costs. *Expert Systems with Applications, 227*, 120275.
4. Chen, T.-K., Liao, H.-H., Chen, G.-D., Kang, W.-H., & Lin, Y.-C. (2023). Bankruptcy prediction using machine learning models with the text-based communicative value of annual reports. *Expert Systems with Applications, 233*, 120714.
5. Chakroun, F., Abid, L., Elarbi, D., & Masmoudi, A. (2024). Gamma-Lindley regression cure model for corporate credit default prediction. *Expert Systems with Applications, 257*, 125004.
6. Chen, X., Liu, J., & Wu, C. (2025). Multi-class financial distress prediction based on hybrid feature selection and improved stacking ensemble model. *Expert Systems with Applications, 282*, 127832.
7. Chang, R., Liu, X., & Deng, W. (2025). Prediction of corporate default risk considering ESG performance and unbalanced samples. *Applied Soft Computing, 171*, 112864.
8. Sun, Y. (2024). Financial distress prediction based on deep learning model. *Procedia Computer Science, 243*, 1069–1078.
9. Förch Brenes, R., Johannssen, A., & Chukhrova, N. (2022). An intelligent bankruptcy prediction model using a multilayer perceptron. *Intelligent Systems with Applications, 16*, 200136.
10. Xiong, X., Jiang, M., Yu, X., Fang, X., Zhao, H., Liu, Y., & Wang, J. (2026). Multi-modal bankruptcy risk prediction for listed companies via large language models. *Information Sciences, 744*, 123387.
11. Tikkhaviro, J. K., & Lukman, B. (2026). Bankruptcy prediction analysis of companies in Indonesia using ensemble learning methods to improve prediction accuracy. *IEHNS 2026.*
12. Rosli, I., Zuber, I. H., Canda, R., & Abdul Wahab, Z. (2025). Bankruptcy prediction using Random Forest for financial risk assessment. *ICERCS 2025.*
13. He, Z. (2025). Enterprise bankruptcy prediction algorithm based on graph neural network. *ICSECE 2025.*
14. Huang, Z. (2025). Evaluating hybrid machine learning models for bankruptcy prediction. *ISCBI 2025.*
15. Arya, A., Soni, T., Uppal, M., & Saini, S. (2024). Integrating multiple machine learning algorithms for bankruptcy prediction: The role of voting classifiers. *ICAICCIT 2024.*
16. Khudhur, A. A. (2024). The power of machine learning in bankruptcy prediction: Application on Taiwanese organizations. *OIDT 2024.*
17. Sabri, N., Md Sahiq, A. N., Mohamed Hamzah, H. H., Sain, H., Abu Mangshor, N. N., & Shari, A. A. (2024). Prediction of bankruptcy among Middle 40 Per Cent (M40) in Malaysia using Support Vector Machine. *SCOReD 2024.*
18. Murugan, S., Le, H. A., Nguyen, H. H., Pham, V. T., Nguyen, V. Q., & Le, T.-L. (2023). Designing a bankruptcy prediction system using Function-Link Cerebellar Model Neural Network. *ICSSE 2023.*
19. Rout, M., & Nayak, S. M. (2023). Genetic algorithm and GAN based hybrid model for bankruptcy prediction. *OCIT 2023.*
20. Kothuru, V., Jha, R. K., Ranjit, S., Reddy, B. V. K., Roy, S., & Sudheer, S. (2022). Prediction of bankruptcy of a company using machine learning techniques. *ICESC 2022.*
21. Vinogradova, A. V., Lazarev, A. I., & Kharlamov, P. S. (2021). Software for data analysis and prediction of bankruptcy of organizations in the fuel and energy complex. *REEPE 2021.*
22. Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. *The Journal of Finance, 23*(4), 589–609.
23. Ohlson, J. A. (1980). Financial ratios and the probabilistic prediction of bankruptcy. *Journal of Accounting Research, 18*(1), 109–131.
24. Zmijewski, M. E. (1984). Methodological issues related to the estimation of financial distress prediction models. *Journal of Accounting Research, 22*, 59–82.
25. Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation, 9*(8), 1735–1780.
26. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems, 30*.
