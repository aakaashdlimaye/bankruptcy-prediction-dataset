# Bankruptcy Prediction Dataset — Quarterly Financial Ratio Sequences

Dataset for a BTech capstone on **bankruptcy prediction from temporal sequences
of quarterly financial ratios**, US listed non-financial firms, 2010–2024.
Built entirely from free sources: SEC EDGAR XBRL company facts, EDGAR 8-K Item
1.03 filings, and the Florida-UCLA-LoPucki Bankruptcy Research Database.

**This repository builds the dataset only. No model training.**

Each example is an 8-quarter window of 29 features for one firm, labelled with
four horizons: did the firm file for bankruptcy within 1, 2, 3 or 4 quarters
after the window's end?

---

## 1. What it produces

| Output | Contents |
|---|---|
| `data/processed/sequences_{train,val,test}.npz` | `X` [n, 8, 29] z-scored, `y` [n, 4], plus mask, indicators and index arrays |
| `data/processed/split_manifest.csv` | one row per window: firm, quarter range, split, labels |
| `data/processed/ratios_panel.parquet` | firm-quarter × 29 ratios, winsorised and raw |
| `data/processed/labels.csv` | one row per bankrupt firm; `labels_events.csv` one row per event |
| `data/processed/scaler_params.json`, `winsor_bounds.json` | train-only normalisation parameters |
| `reports/` | gate evidence and the dataset report (see §6) |

Headline numbers for the pilot run are in
[`reports/DATASET_REPORT.md`](reports/DATASET_REPORT.md).

---

## 2. Environment setup

Python 3.11+ (built and tested on 3.13), ~4 GB free disk, no API keys.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

On Linux/macOS use `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

### SEC etiquette (required)

Every request to `sec.gov` / `data.sec.gov` sends a descriptive User-Agent, and
requests are throttled to 8/second (under the SEC's 10/s limit). The contact
address is set in `src/config.py` and can be overridden without editing code:

```bash
export SEC_EMAIL="you@example.com"
```

The address is sent **only** to the SEC. UCI downloads in Phase 6 use a
neutral User-Agent.

### One manual download

The LoPucki Cases table cannot be fetched programmatically. Download it from
<https://lopucki.law.ufl.edu> ("Download cases table") and save it as:

```
data/raw/lopucki_cases.csv
```

If it is absent, Phase 1 prints instructions and continues with the two EDGAR
label sources; the pipeline still completes.

---

## 3. Reproducing everything

```bash
.venv/Scripts/python.exe run_all.py
```

That runs Phases 0–7 on the pilot universe from an empty `data/`, downloading
~3.0 GB of SEC bulk files on first run and caching them thereafter. Roughly
25–40 minutes cold, ~4 minutes warm.

Equivalently, with `make`:

```bash
make venv && make all
```

Useful variants:

```bash
python run_all.py --from 3        # resume at a phase
python run_all.py --only 4 5      # run selected phases
python run_all.py --force         # ignore caches and rebuild
python run_all.py --embargo       # stricter split: drop boundary-straddling windows
python run_all.py --full --from 3 # full universe (see the estimate first)
```

Run the phases individually if preferred:

```bash
python src/download_bulk.py         # Phase 0  bulk downloads
python src/scan_submissions.py      # one pass over submissions.zip
python src/phase1_labels.py         # Phase 1  bankruptcy labels
python src/phase2_universe.py       # Phase 2  universe + pilot sample
python src/phase3_fundamentals.py   # Phase 3  XBRL extraction
python src/phase4_ratios.py         # Phase 4  ratios
python src/verify_ratios.py         # Phase 4  hand-recomputation gate
python src/phase5_sequences.py      # Phase 5  sequences, split, leakage audit
python src/phase6_external.py       # Phase 6  UCI datasets
python src/phase7_report.py         # Phase 7  dataset report
python src/estimate_full_run.py     # Phase 7  --full time/disk estimate
python -m pytest tests/ -q          # 53 unit tests
```

Every phase is idempotent and checkpointed: completed downloads and extraction
chunks are skipped, so an interrupted run resumes where it stopped.

### The `--full` flag

`--full` runs the identical pipeline over all in-scope non-financial firms
instead of the pilot sample, writing to separate files
(`fundamentals_panel_full.parquet`, `ratios_panel_full.parquet`) so pilot
artefacts are never overwritten. It makes no additional SEC requests.
Measured estimate: see [`reports/full_run_estimate.md`](reports/full_run_estimate.md).
**It has not been launched**, per the build instructions.

---

## 4. Viewing the data

The headline outputs are Parquet and NPZ, which no text editor will open.
`src/peek.py` prints them:

```bash
python src/peek.py                       # what exists, shapes, sizes
python src/peek.py labels                # bankrupt firms, by source and year
python src/peek.py panel                 # raw XBRL inputs per firm-quarter
python src/peek.py ratios                # the 29 features per firm-quarter
python src/peek.py manifest              # one row per 8-quarter window
python src/peek.py sequences --split test    # tensors, incl. a worked example window
python src/peek.py firm 320193           # one company, end to end
python src/peek.py firm "TOYS R US"      # ...by name too
python src/peek.py export ratios out.csv # dump any table to CSV or .xlsx
```

`peek.py firm` is the most useful view: it shows the raw XBRL inputs, **which
XBRL tag supplied each value**, the resulting ratios, and the sequence windows
built from them — the whole chain for one company on one screen.

The `reports/` directory is plain Markdown and CSV; open those in any editor.

In Python:

```python
import pandas as pd, numpy as np
ratios = pd.read_parquet("data/processed/ratios_panel.parquet")
with np.load("data/processed/sequences_train.npz") as z:
    X, y = z["X"], z["y"]          # (12634, 8, 29), (12634, 4)
```

## 5. Data dictionary

### `data/processed/sequences_{train,val,test}.npz`

| Array | Shape | dtype | Meaning |
|---|---|---|---|
| `X` | [n, 8, 29] | float32 | Z-scored features. Axis 1 is time, oldest quarter first. Cells missing after forward fill are set to the train mean (0 after scaling). |
| `X_unscaled` | [n, 8, 29] | float32 | Same windows, winsorised but not standardised. |
| `mask` | [n, 8, 29] | uint8 | 1 = value observed, 0 = imputed. |
| `y` | [n, 4] | int8 | Columns are horizons h = 1, 2, 3, 4. `y[i, h-1] = 1` if the firm filed within h quarters of the window's end quarter. |
| `indicators` | [n, 8, 2] | float32 | `has_inventory`, `has_debt` (see §6). Not part of the 29 features. |
| `cik` | [n] | U12 | SEC Central Index Key, unpadded. |
| `start_quarter`, `end_quarter` | [n] | U6 | e.g. `2018Q2`. Split is determined by `end_quarter`. |
| `is_positive_firm` | [n] | int8 | 1 if the firm ever files for bankruptcy in the study window. |
| `feature_names` | [29] | U40 | Column names for axis 2 of `X`, in order. |
| `indicator_names` | [2] | U20 | Column names for axis 2 of `indicators`. |
| `horizons` | [4] | int8 | `[1, 2, 3, 4]`. |

### `data/processed/split_manifest.csv`

One row per window. `cik`, `company`, `start_quarter`, `end_quarter`,
`start_quarter_idx`, `end_quarter_idx` (monotone integer quarter index),
`split`, `is_positive_firm`, `event_date`, `quarters_to_event`,
`n_observed_quarters` (of 8, excluding forward-filled), `pct_cells_present`,
`y1`–`y4`.

### `data/processed/ratios_panel.parquet`

`cik`, `company`, `sic`, `is_bankrupt`, `quarter`, `quarter_idx`,
`period_end`, `fy`, `fp`, then:

- the 29 winsorised features (`r01_current_ratio` … `r29_negative_equity_flag`)
- the same 29 pre-winsorisation under a `raw__` prefix
- `has_inventory`, `has_debt`

### `data/interim/fundamentals_panel.parquet`

One row per firm-quarter, one column per input concept, plus derived
`TotalDebt`, `CurrentDebt`, `EBIT`, `EBITDA`. Every value column has a
companion `<concept>__src` provenance column holding `"<xbrl_tag>|<method>"`,
where method is `direct`, `differenced`, `derived`, `identity`, `annual_div4`
or `non_overlapping`. This is what makes every number in the dataset traceable
back to a specific XBRL fact.

### `data/processed/labels.csv`

`cik`, `company`, `event_date` (first event inside 2010–2024), `prior_event_date`,
`n_events`, `all_event_dates`, `source`, `chapter`, `sic`, `is_primary_filer`,
`date_discrepancy_days`, `in_window`. `labels_events.csv` has one row per
distinct bankruptcy event for firms that filed more than once.

### `data/universe_pilot.csv`

The pilot firm list: all in-scope bankrupt firms plus a seeded (`seed=42`)
random sample of survivors.

---

## 6. Feature list

The 29 features are the 28 ratios from the capstone spec plus a negative-equity
flag.

| # | Feature | Family | Formula |
|---|---|---|---|
| 1 | `r01_current_ratio` | Liquidity | CA / CL |
| 2 | `r02_quick_ratio` | Liquidity | (CA − Inventory) / CL |
| 3 | `r03_cash_ratio` | Liquidity | Cash / CL |
| 4 | `r04_wc_to_ta` | Liquidity | (CA − CL) / TA — Altman X₁ |
| 5 | `r05_net_profit_margin` | Profitability | NI / Revenue |
| 6 | `r06_roa` | Profitability | NI / TA |
| 7 | `r07_roe` | Profitability | NI / Equity |
| 8 | `r08_ebitda_margin` | Profitability | EBITDA / Revenue |
| 9 | `r09_ebit_to_ta` | Profitability | EBIT / TA — Altman X₃ |
| 10 | `r10_re_to_ta` | Profitability | Retained earnings / TA — Altman X₂ |
| 11 | `r11_debt_to_equity` | Leverage | Total debt / Equity |
| 12 | `r12_debt_to_assets` | Leverage | Total debt / TA |
| 13 | `r13_interest_coverage` | Leverage | EBIT / Interest expense |
| 14 | `r14_equity_to_liabilities` | Leverage | Equity / Total liabilities — Altman X₄ (book, Z′/Z″ form) |
| 15 | `r15_ltd_to_ta` | Leverage | Long-term debt / TA |
| 16 | `r16_asset_turnover` | Efficiency | Revenue / TA — Altman X₅ |
| 17 | `r17_inventory_turnover` | Efficiency | COGS / Inventory |
| 18 | `r18_receivables_turnover` | Efficiency | Revenue / AR |
| 19 | `r19_payables_turnover` | Efficiency | COGS / AP |
| 20 | `r20_cash_conversion_cycle` | Efficiency | DIO + DSO − DPO, days |
| 21 | `r21_revenue_growth` | Growth | (Revₜ − Revₜ₋₄) / \|Revₜ₋₄\| |
| 22 | `r22_net_income_growth` | Growth | (NIₜ − NIₜ₋₄) / \|NIₜ₋₄\| |
| 23 | `r23_assets_growth` | Growth | (TAₜ − TAₜ₋₄) / TAₜ₋₄ |
| 24 | `r24_equity_growth` | Growth | (Eqₜ − Eqₜ₋₄) / \|Eqₜ₋₄\| |
| 25 | `r25_ocf_to_cl` | Cash flow | OCF / CL |
| 26 | `r26_fcf_to_ta` | Cash flow | (OCF − CapEx) / TA |
| 27 | `r27_accrual_quality` | Cash flow | OCF / NI |
| 28 | `r28_ocf_to_debt` | Cash flow | OCF / Total debt |
| 29 | `r29_negative_equity_flag` | Distress | 1 if Equity < 0 |

**Conventions.** Flows are *quarterly*, so margins and turnovers are quarterly
magnitudes — roughly a quarter of their annual equivalents. `Total debt` is
interest-bearing debt (short-term borrowings + current LTD + non-current LTD),
never total liabilities; ratio 14 is the only one that uses total liabilities,
because that is what Altman specified. A quarter is 91.25 days for the cash
conversion cycle.

**Undefined ≠ missing.** Firms without inventory (`has_inventory = 0`: absent
or zero in ≥ 6 of the firm's 8 most recent quarters) get NaN for ratios 2, 17
and 20 rather than an imputed number. Firms that never report debt or interest
expense (`has_debt = 0`) get NaN for ratio 13. Both indicators travel with the
data in the `indicators` array.

---

## 7. Reports

| File | What it shows |
|---|---|
| [`DATASET_REPORT.md`](reports/DATASET_REPORT.md) | Firm/sequence/positive counts per split and horizon, coverage summary, every known caveat |
| [`labels_report.md`](reports/labels_report.md) | Label counts per source, cross-source overlap, per-year distribution |
| [`universe_report.md`](reports/universe_report.md) | Universe funnel and SIC resolution |
| [`coverage_report.md`](reports/coverage_report.md) | Per-concept coverage, YTD de-cumulation stats, ASC 606 tag-switch evidence |
| [`ratios_report.md`](reports/ratios_report.md) | Per-ratio distributions before/after winsorisation, missingness heatmap |
| [`hand_check.md`](reports/hand_check.md) | Phase 4 gate: 5 firm-quarters recomputed by hand from raw XBRL facts |
| [`sequences_report.md`](reports/sequences_report.md) | Dropout-trap distribution, completeness rule, window counts |
| [`leakage_audit.md`](reports/leakage_audit.md) | Phase 5 gate: four leakage checks with printed evidence |
| [`external_datasets_report.md`](reports/external_datasets_report.md) | UCI Taiwanese/Polish descriptions, Kaggle instructions |
| [`full_run_estimate.md`](reports/full_run_estimate.md) | Measured time/disk estimate for `--full` |
| [`unmatched_positives.csv`](reports/unmatched_positives.csv) | Every labelled bankrupt firm that could not enter the panel, with a reason |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every judgment call, with rationale |

---

## 8. Repository layout

```
src/
  config.py               paths, SEC etiquette, XBRL tag chains, split spec
  sec_client.py           rate-limited, cached, resumable HTTP for sec.gov
  download_bulk.py        Phase 0  bulk downloads
  scan_submissions.py     one pass over submissions.zip -> metadata + 8-K items
  phase1_labels.py        Phase 1  labels from three sources
  phase2_universe.py      Phase 2  universe and pilot sample
  xbrl_extract.py         fact -> firm-quarter, incl. YTD de-cumulation
  phase3_fundamentals.py  Phase 3  extraction and derived quantities
  phase4_ratios.py        Phase 4  the 29 features
  verify_ratios.py        Phase 4  hand-recomputation gate
  phase5_sequences.py     Phase 5  labelling, windows, split, leakage audit
  peek.py                 browse the built dataset from the CLI
  phase6_external.py      Phase 6  UCI/Kaggle supplementary sets
  phase7_report.py        Phase 7  dataset report
  estimate_full_run.py    Phase 7  --full estimate
tests/                    53 unit tests, incl. both YTD filer styles
data/{raw,interim,processed,external}
docs/DECISIONS.md
reports/
run_all.py                orchestrator
Makefile
```

---

## 9. Known limitations

Summarised here; quantified in `reports/DATASET_REPORT.md` §4.

- **Pilot is positive-enriched.** Positives are never subsampled and already
  exceed the ~500-firm pilot budget, so pilot class rates are not population
  rates. `--full` restores the true base rate.
- **Interest expense** is the weakest input, as the spec predicts. The
  annual ÷ 4 fallback fills a reported share of cells; ratio 13 takes the
  heaviest winsorisation of any ratio.
- **Total debt** is NaN for firms that tag long-term debt only annually,
  rather than being silently read as zero.
- **COGS and accounts payable** have real gaps because the common alternative
  tags (`CostsAndExpenses`, `AccountsPayableAndAccruedLiabilitiesCurrent`) are
  different concepts and are deliberately not substituted.
- **Right-censoring.** Survivors that stop filing after an acquisition or
  going private are labelled 0 and not distinguished from continuing firms.
- **Stride-1 boundary overlap.** Input quarters near a split boundary can
  appear in windows on both sides; no label is shared. `--embargo` removes
  those windows.
- **LoPucki coverage ends December 2022** and only covers large firms; it
  enriches the EDGAR labels rather than defining them.

---

## 10. Sources

- SEC EDGAR XBRL company facts — <https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip>
- SEC EDGAR bulk submissions — <https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip>
- EDGAR full-text search — <https://efts.sec.gov/LATEST/search-index>
- Florida-UCLA-LoPucki BRD — <https://lopucki.law.ufl.edu>
- UCI Taiwanese Bankruptcy Prediction — <https://archive.ics.uci.edu/dataset/572>
- UCI Polish Companies Bankruptcy — <https://archive.ics.uci.edu/dataset/365>
