# Session Summary — Dataset Build

**Date:** 1 September 2026
**Scope:** Build the complete dataset for the capstone *"Bankruptcy Prediction using
Temporal Deep Learning: A Comparative Study of LSTM and Transformer Models."*
**Explicitly out of scope:** model training. Nothing in this repository fits a model.

---

## 1. What exists now

A reproducible pipeline that turns three free public sources into model-ready
tensors, plus the evidence needed to defend every number in a viva.

| Layer | Output | Size |
|---|---|---|
| Bankruptcy labels | 2,473 firms (1,066 inside 2010–2024), 2,736 distinct events | `labels.csv`, `labels_events.csv` |
| Quarterly fundamentals | 40,691 firm-quarters × 30 XBRL concepts, each with provenance | `fundamentals_panel.parquet` |
| Features | 40,691 firm-quarters × 29 ratios, winsorised + raw | `ratios_panel.parquet` |
| Sequences | 18,000 windows of `[8 quarters × 29 features]`, 4 horizons | `sequences_{train,val,test}.npz` |
| External validation | UCI Taiwanese (6,819 firms), UCI Polish (5 horizons) | `data/external/` |

Everything rebuilds from an empty `data/` with one command, verified by an
actual clean-room run this session:

```bash
python run_all.py
```

---

## 2. What was done, phase by phase

**Phase 0 — Scaffold.** Repo layout, venv, pinned-minimum requirements. All SEC
traffic routed through one client that enforces the mandatory User-Agent, an
8 req/s token bucket (under the 10/s ceiling), retry/backoff, disk caching and
resumable range downloads. No other module can bypass it.

**Phase 1 — Labels first.** The spec's ordering was followed deliberately: the
positive-class size determines whether anything downstream is viable.

- EDGAR full-text search swept year-by-year 2009–2025, filtered on the
  structured `items` field rather than text matching (the query `"Item 1.03"`
  also matches filings that merely *mention* the item).
- **A third source was added**: the `items` field carried on every 8-K inside
  bulk `submissions.zip`. This is the authoritative, non-paginated version of
  the same signal and found **2,000 CIKs against the full-text sweep's 1,258**.
- LoPucki BRD joined on CIK, then fuzzy name (≥90 accept, 80–90 to a manual
  review file, below 80 logged as unmatched).

Gate: ≥250 bankrupt firms in 2010–2024. **Result: 1,066.**

**Phase 2 — Universe.** 10,758 non-financial firms with a 10-K/10-Q period end
in window and a companyfacts entry. SIC resolved through a three-source chain;
firms with no resolvable SIC are kept and flagged rather than dropped, since
dropping them would silently discard bankrupt micro-caps. Pilot = all 789
in-scope positives + 789 seeded survivors.

**Phase 3 — Fundamentals.** Extraction from `companyfacts.zip` with the full
fallback chains and, critically, YTD de-cumulation. Two reconstruction routes
were implemented, not one:

| Route | Quarter-values |
|---|---:|
| reported directly as an 80–100 day quarter | 283,172 |
| `Qn = YTD(n) − YTD(n−1)` (the spec's route, for YTD filers) | 314,187 |
| `Q4 = FY − Q1 − Q2 − Q3` (added, for discrete-quarter filers) | 1,038 |

The second route was added because a filer reporting only discrete quarters has
no cumulative prefix to subtract, so its Q4 — present in the 10-K only as an
annual total — would otherwise be unrecoverable. **Differencing supplies 52.7%
of all flow observations**; 75% of OCF cells and 73% of CapEx cells are
reconstructed. Gate passed.

**Phase 4 — Ratios.** All 28 formulas plus the negative-equity flag, with the
undefined-vs-missing rules, YoY growth matched on quarter index (never
positionally), and winsorisation fitted on the training period only. Gate: five
random firm-quarters recomputed by hand **from the raw XBRL JSON**, printing the
actual subtraction arithmetic. 145 ratio comparisons, 0 mismatches.

**Phase 5 — Sequences.** Post-petition rows removed (3,832), horizon labels
measured in real time from period end, bounded forward-fill, 8-quarter windows,
chronological split by end quarter, scaler fitted on train only. Gate: the
four-check leakage audit, all passing with printed evidence.

**Phase 6 — External sets.** UCI Taiwanese and Polish downloaded and described.
Kaggle needs an API token, so instructions were written into the README and the
step skipped rather than blocking, per the spec.

**Phase 7 — Deliverables.** `DATASET_REPORT.md` (every figure read from disk, no
hard-coded numbers), completed README with data dictionary, `DECISIONS.md` with
every judgment call, and a measured `--full` estimate.

---

## 3. Four defects found and fixed

These matter for the write-up because each would have silently corrupted results
rather than crashing.

**1. Distinct bankruptcies were being merged into one.** The spec's "keep the
earlier date" rule, applied across a firm's whole history, overwrote PG&E's 2019
filing with LoPucki's 2001 date and pushed it out of the study window. Fixed with
365-day event clustering, so the rule now applies *within* an event. PG&E (2019),
NRG (2017) and Trump Entertainment (4 filings) all resolve correctly.

**2. Over-aggressive name normalisation produced false matches.** Stripping
descriptive words reduced *Frontier Communications Corp* to `frontier`, which
collided with a 1986 *Frontier Holdings Inc* case at score 100 and backdated
Frontier's 2020 bankruptcy to 1986. Only legal-form suffixes are stripped now.

**3. `TotalDebt` was silently wrong for annual-only debt taggers.** Many filers
tag long-term debt only in the 10-K. Treating the missing quarters as zero turned
Toys R Us's stable $4.8bn debt load into a sawtooth between $4.9bn and $0.1bn.
A component now counts as zero only if the firm never reports it anywhere;
otherwise the quarter is NaN. Separately, when the chain lands on `LongTermDebt`
(which already includes current maturities), adding the current portion was
double-counting.

**4. Phantom rows were depressing every coverage figure.** companyfacts
income-statement comparatives reach further back than balance-sheet
comparatives, creating sparse rows that supported almost no ratio. `Assets` was
reading 86% when essentially every 10-Q tags it. Restricting the panel to
balance-sheet-anchored quarters removed 13.5% of rows and lifted every Tier-1
concept above the 90% gate.

---

## 4. The outputs, and what each is for

### `sequences_{train,val,test}.npz` — the model input

| Split | Windows | Firms | y1 | y2 | y3 | y4 | y4 rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| train ≤2019Q4 | 12,634 | 813 | 154 | 410 | 693 | 986 | 7.80% |
| val 2020Q1–21Q4 | 2,357 | 375 | 37 | 71 | 92 | 108 | 4.58% |
| test 2022Q1–24Q4 | 3,009 | 370 | 60 | 158 | 260 | 363 | 12.06% |

`X` is `[n, 8, 29]` z-scored, `y` is `[n, 4]`. Also carried: `mask` (1 =
observed, 0 = imputed), `indicators` (`has_inventory`, `has_debt`),
`X_unscaled`, and `cik` / `start_quarter` / `end_quarter` index arrays.

The `mask` array is not decoration — it lets you exclude imputed cells from
attention-weight analysis, which is what keeps Contribution 4 honest.

### `ratios_panel.parquet` and `fundamentals_panel.parquet`

The firm-quarter panel before windowing. You need these for the classical
baselines, which are computed from *levels*, not from the 29 ratios: Ohlson's
O-score needs raw total assets and total liabilities, Zmijewski needs NI/TA,
TL/TA and CA/CL. All those inputs are ≥95% covered.

`fundamentals_panel.parquet` also carries a `<concept>__src` provenance column
for every value, recording which XBRL tag and which method produced it. That is
what lets you answer "where did this number come from?" for any cell in the
dataset — useful in a viva, and the basis of the data-quality section of the paper.

### `reports/` — the evidence

Ten Markdown reports plus three CSVs. Four are gate evidence and are worth
reading before writing the methodology section: `coverage_report.md` (including
the ASC 606 tag-switch table), `hand_check.md`, `leakage_audit.md`,
`sequences_report.md`.

---

## 5. Relevance to the research

### It delivers Contribution 1 outright

*"A temporal panel dataset of US listed non-financial firms built from free
sources and released publicly — addressing the cross-sectional monoculture of the
UCI datasets used by 7 of the 21 reviewed papers."* That contribution is now a
built artefact rather than a plan. The UCI sets sit in `data/external/` for
exactly the contrast the claim rests on: 6,819 firms, single snapshot, no time
axis, versus 18,000 windows with an 8-quarter history each.

### The decomposition experiment (Models A→B→C→D) is directly runnable

Models A, B and C all use Altman's five variables — ratios 4, 10, 9, 14, 16.
Their completeness inside the tensors was checked:

| Split | Per-cell observed | Windows with all 5 complete across all 8 quarters |
|---|---:|---:|
| train | 99.0% | 91.1% |
| val | 99.4% | 94.9% |
| test | 99.5% | 95.1% |

So the A→B→C→D ladder is not gated on data availability. One methodological
note: to keep the gaps attributable, **Models A and B must be evaluated on the
same window set as C and D**, using the end quarter (`t-0`) of each window as
their single-period input. Scoring the static models on a different row set would
confound the comparison with sample differences.

Ratio 14 is the **book-value** X₄, so what you have is Z′/Z″, not the 1968 Z.
That is the correct choice for a mixed non-financial sample and matches the
spec's own guidance — but the paper must label it Z″ explicitly, never "Altman
X₄" unqualified.

### Contribution 5 is where the dataset does the most work

*"A methodological audit showing that reported accuracies of 91–99% arise from
balanced samples, random splits and accuracy-on-imbalanced-data."* Three
properties of this build support that claim directly:

- a **chronological** split, assigned by window end quarter, with a leakage
  audit that prints its evidence;
- **four horizons** rather than one, so "predicting bankruptcy" is stated
  precisely instead of left ambiguous;
- **realistic missingness** — the ratios most papers assume are free
  (interest coverage, total debt) are the ones that are hardest to obtain, and
  the coverage report quantifies exactly that.

**One caveat is load-bearing here**: the pilot is deliberately positive-enriched
(789 positives, 789 survivors) because the spec forbids subsampling positives and
they already exceed the ~500-firm budget. Its class rates are **not** population
rates. A paper claiming to demonstrate performance at realistic base rates cannot
be run on the pilot alone — see §6.

---

## 6. How to proceed

### Step 1 — Run `--full` before any headline results

This is the highest-priority next action, and it is a genuine decision rather
than a formality. The pilot exists to validate the pipeline, which it has done.
But its ~50% firm-level positive rate is an artefact of construction. The full
universe carries roughly 7% bankrupt firms, and Contribution 5 depends on
reporting results at that base rate.

```bash
python run_all.py --full --from 3
```

Measured estimate: **~28 minutes, ~3.2 GB total disk**, no additional SEC
requests (it reads bulk files already cached). Outputs go to
`fundamentals_panel_full.parquet` / `ratios_panel_full.parquet`, so pilot
artefacts survive for comparison. It was deliberately not launched this session,
per the build instructions.

Sensible practice: report the full run as the primary result and keep the pilot
as a sensitivity check.

### Step 2 — Start the modelling repo separately

Keep this repository as the dataset artefact. A model repo consumes it in four
lines:

```python
import numpy as np
with np.load("data/processed/sequences_train.npz") as z:
    X, y, mask = z["X"], z["y"], z["mask"]     # (n, 8, 29), (n, 4), (n, 8, 29)
```

Choose a horizon (`y[:, 0]` for h=1 … `y[:, 3]` for h=4) or train the
multi-horizon head from Korangi et al. that the spec lists as a should-do.

### Step 3 — Classical baselines from the panel, not the tensors

Altman Z″, Ohlson O-score and Zmijewski are computed from levels. Join back to
`ratios_panel.parquet` / `fundamentals_panel.parquet` on `(cik, quarter)` using
`split_manifest.csv` to keep the row set identical to the deep models. Report
Altman both as a threshold-free AUC and at its canonical cutoffs — the spec is
right that reporting only the latter looks rigged.

### Step 4 — Imbalance handling belongs to you, not to this repo

SMOTE, class weights, focal loss (γ=2, α=0.25) and cost-sensitive thresholds
were deliberately **not** applied here. Resampling before the split would leak;
resampling after belongs in the training loop where it can be ablated. The
tensors are untouched so that ablation is clean.

### Step 5 — Robustness checks worth budgeting for

- `python run_all.py --embargo` drops boundary-straddling windows for a stricter
  split. Reporting both is a cheap, credible robustness result.
- The UCI Taiwanese and Polish sets support the cross-market check and, more
  usefully, a direct demonstration of Contribution 5: run the same architecture
  on UCI with a random split and on this dataset with a chronological one, and
  show the gap.

### Step 6 — Optional extensions, in priority order

1. **Market channel** (yfinance) for the true 1968 X₄ and realised volatility.
   Note the spec's warning: Yahoo drops delisted tickers, which is exactly the
   positive class. Treat it as an ablation on a subset, not a core feature.
2. **Kaggle US set** as an independent label cross-check (needs an API token;
   instructions in the README).
3. **Wider window** — the spec allows 8–10 quarters. `WINDOW_LEN` in
   `src/config.py` is the only change needed.

---

## 7. Caveats to carry into the paper

These are quantified in `reports/DATASET_REPORT.md` §4 and should appear in the
data section rather than being discovered by a reviewer.

| Caveat | Figure |
|---|---|
| Pilot is positive-enriched; class rates are not population rates | 789 / 789 firms |
| `InterestExpense` needs the annual÷4 fallback | 73.7% raw, 95.7% over the defined population |
| Ratio 13 takes the heaviest winsorisation of any ratio | clipped to [−2044, 619] |
| `TotalDebt` NaN where filers tag debt only annually | 43.6% raw coverage |
| `COGS` / `InventoryNet` structurally absent for service firms | 56.2% / 54.1% raw |
| Revenue gap is mostly structural, not a tagging failure | 87.0% raw → 97.6% defined |
| Positives that could not be joined to fundamentals | 283 of 1,066, each with a logged reason |
| Bankrupt firms stop filing before the petition | median 1 quarter; 49% stop ≥2 quarters ahead |
| Survivors that stop filing are right-censored, labelled 0 | not distinguished from continuing firms |
| Ratio 14 is book-value X₄ (Z′/Z″), not the 1968 market form | — |
| Stride-1 windows share input quarters across split boundaries | no labels shared; `--embargo` removes |

Two deliberate refusals worth defending if challenged: `CostsAndExpenses` was
**not** used as a COGS fallback (it is total costs including SG&A) and
`AccountsPayableAndAccruedLiabilitiesCurrent` was **not** used for accounts
payable (it is a different concept). Both would have raised coverage while
silently changing what ratios 17, 19 and 20 measure. Honest missingness was
preferred over imputation artefacts, consistent with the spec's own stance.

---

## 8. Quick reference

```bash
python run_all.py                    # rebuild everything (pilot)
python run_all.py --full --from 3    # full universe
python -m pytest tests/ -q           # 53 unit tests
python src/peek.py                   # browse outputs
python src/peek.py firm "TOYS R US"  # one company, raw facts -> ratios -> windows
```

**Status:** all seven acceptance criteria verified this session, including a
clean-room rebuild from an empty `data/`.

**Housekeeping:** `data/raw/` holds 2.8 GB of SEC bulk files. The folder is not
yet a git repository; add `data/`, `.venv/` and `__pycache__/` to `.gitignore`
before the first commit, and keep `data/raw/lopucki_cases.csv` noted in the
README as the one manual download.
