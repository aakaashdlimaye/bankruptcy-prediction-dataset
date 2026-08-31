# PROMPT FOR CLAUDE CODE — paste everything below this line

You are building the complete dataset for a BTech capstone research project: **bankruptcy prediction from temporal sequences of quarterly financial ratios** for US listed non-financial firms, 2010–2024. Your job is ONLY the dataset — no model training. Work autonomously, phase by phase, until every acceptance criterion at the bottom passes. Do not stop at the first working version of a phase; run its validation gate, fix what fails, and only then move on. If something is ambiguous, make the most defensible choice, log it in `docs/DECISIONS.md`, and continue — do not wait for me unless the choice would be irreversible.

## Context files (read these first, in this order)

1. `Dataset_Sources_and_Ratio_Derivability_Summary.md` — the data spec: all source URLs, the full XBRL tag-mapping tables with fallback chains, and the three structural traps (interest expense, YTD de-cumulation, undefined-vs-missing). Treat its tag tables as authoritative.
2. `Capstone_Summary.md` — project context. Section 5 has the 28-ratio formula table; Section 6 has the window/split spec.
3. `data/raw/lopucki_cases.*` — the Florida-UCLA-LoPucki BRD Cases table (already downloaded). If absent, tell me to download it from lopucki.law.ufl.edu and continue with all other work in the meantime.

## Environment

- Desktop, 32 GB RAM, ample disk. Python 3.11+. Create a venv; use pandas, pyarrow, requests, tqdm, numpy. No paid services, no API keys.
- SEC etiquette is mandatory: every request to sec.gov/data.sec.gov must send a User-Agent header of the form `"Aakaash Limaye <email> MPSTME capstone research"` (ask me once for the email at the start, then proceed); max 10 requests/sec; prefer bulk files over per-company API calls wherever possible.
- Everything must be reproducible: each phase is a standalone script in `src/`, orchestrated by a `Makefile` or `run_all.py`. Cache all downloads under `data/raw/`; never re-download something that exists and passes a size/hash check. Checkpoint long loops so any script can resume after interruption.

## Build strategy: pilot first, then scale

Build and validate the ENTIRE pipeline end-to-end on a pilot universe before scaling:

- **Pilot universe = ALL bankrupt firms you can identify + a random sample of non-bankrupt firms, totalling ~500 firms.** Never subsample the positive class — it is only ~3% of firms and every positive matters. Seed the random sample (seed=42) and save the firm list to `data/universe_pilot.csv`.
- Only after every acceptance criterion passes on the pilot, add a `--full` flag path that runs the same pipeline over the full non-financial universe. Implement the flag and estimate full-run time/disk, but DO NOT launch the full run — report the estimate and stop there.

## Phase 0 — Scaffold

Create the repo layout (`src/`, `data/raw/`, `data/interim/`, `data/processed/`, `docs/`, `reports/`), the venv, `requirements.txt`, and a `README.md` skeleton you will fill as you go.

## Phase 1 — Bankruptcy labels (do this BEFORE fundamentals)

Positive-class size determines whether everything downstream is viable, so labels come first.

1. **8-K Item 1.03 sweep:** query EDGAR full-text search (`efts.sec.gov/LATEST/search-index?q="Item 1.03"&forms=8-K`) year by year, 2009–2025 (one year of margin each side). Collect CIK, company name, filing date. Handle pagination. The 8-K filing date is the bankruptcy event date.
2. **LoPucki cross-check:** load the Cases table, extract company name, CIK/ticker where present, filing date, chapter. Join to the 8-K set on CIK first, then fuzzy name match (rapidfuzz, threshold ≥ 90, manual-review file for 80–90). Where both sources have a date, keep the earlier one and record the discrepancy.
3. Output `data/processed/labels.csv`: one row per bankrupt firm — CIK, name, event_date, source(s), chapter if known. Also write `reports/labels_report.md`: counts per source, overlap, per-year distribution, and the implied positive rate against a ~7,000-firm universe (sanity target: roughly 2–4%).

**Gate:** at least 250 distinct bankrupt firms with event dates inside 2010–2024. If materially fewer, diagnose (pagination? date parsing? full-text coverage?) before proceeding.

## Phase 2 — Firm universe

1. Download `company_tickers.json`. For universe membership and SIC codes, use the SEC Financial Statement Data Sets (`sub.txt` has SIC per filing) or the submissions API — bulk preferred.
2. Exclude SIC 6000–6799 (financials, insurance, real estate). Keep firms with at least one 10-K or 10-Q between 2010 and 2024.
3. Construct the pilot universe per the strategy above (all positives + seeded sample of survivors ≈ 500 firms). Verify every labelled bankrupt firm's CIK actually resolves to filings; log any that don't to `reports/unmatched_positives.csv` — do not silently drop them.

## Phase 3 — Fundamentals extraction (SEC EDGAR XBRL)

1. Download `companyfacts.zip` once (~1.2 GB). Extract only the JSONs for pilot-universe CIKs.
2. For each firm, extract every input concept in the tag tables of the derivability summary, applying the fallback chains exactly as specified there (Revenue chain including the ASC 606 switch, COGS chain, Total Debt summation, EBIT ≡ `OperatingIncomeLoss`, EBITDA = OperatingIncomeLoss + D&A chain).
3. **Quarterly alignment rules — these are the traps that corrupt data silently:**
   - Keep only facts with `form` in {10-Q, 10-K} and their amendments (prefer the latest amendment per period).
   - For duration (flow) facts, compute the span from `start`/`end`. A true quarter is ~80–100 days. For cumulative YTD facts (common for ALL cash-flow items and for some filers' income items), reconstruct discrete quarters by differencing: Q2 = YTD(Q2) − YTD(Q1), Q3 = YTD(Q3) − YTD(Q2), Q4 = FY − YTD(Q3). Verify spans BEFORE differencing — some filers already report discrete quarters, and differencing those double-subtracts. Unit-test both filer styles with synthetic fixtures.
   - Instant (balance-sheet) facts: take the value at each fiscal quarter end.
   - Deduplicate on (cik, concept, period): prefer 10-K over 10-Q for Q4-equivalent data, latest filing wins.
4. Output `data/interim/fundamentals_panel.parquet`: one row per firm-quarter, one column per input concept, plus fiscal period metadata and a per-value provenance column recording which tag in the fallback chain supplied it.

**Gate:** write `reports/coverage_report.md` with per-concept non-null coverage. Expectations from the spec: Tier-1 concepts ≥ 90% coverage; Revenue ≥ 95% after the fallback chain; InterestExpense may be as low as 70% (known issue — apply the annual÷4 fallback and report how many cells it filled). Investigate anything far below expectation before continuing.

## Phase 4 — Ratio computation (28 + 1 features)

Compute all 28 ratios exactly per the formula table in `Capstone_Summary.md` Section 5, plus:

- **Feature 29:** `negative_equity_flag` (1 if StockholdersEquity < 0). Do not drop negative-equity rows; ROE and Debt-to-Equity for those rows are computed as-is and left to winsorisation.
- **Undefined ≠ missing:** where Inventory is structurally absent (service/software firms — absent in ≥ 6 of the firm's 8 most recent quarters), set ratios 2, 17, 20 to a sentinel (0 for turnover-style after winsorisation is NOT acceptable — use NaN plus a `has_inventory` indicator column and document this). Same logic for Interest Coverage at zero-debt firms via a `has_debt` indicator.
- Growth ratios (21–24) use t vs t−4 within the same firm only; require both quarters present.
- Cash Conversion Cycle: DIO = 365/4 ÷ quarterly inventory turnover, DSO and DPO analogously; document the quarterly convention in `docs/DECISIONS.md`.
- Keep `RetainedEarningsAccumulatedDeficit` negatives as-is.
- Winsorise every ratio at its 1st/99th percentile — computed on the TRAINING period only (filings up to 2019-12-31), then applied to all periods. This is a leakage rule, not a style choice.

Output `data/processed/ratios_panel.parquet` + `reports/ratios_report.md` (per-ratio distributions before/after winsorisation, missingness heatmap by ratio × year, count of sentinel/indicator activations).

**Gate:** recompute 5 randomly chosen firm-quarters' ratios by hand from the raw facts (print the arithmetic) and confirm they match the pipeline output.

## Phase 5 — Labelling firm-quarters and sequence construction

1. For each bankrupt firm, find its LAST available filed quarter. Per the spec's dropout trap: firms stop filing 2–4 quarters before the event — the look-back window must end at the last available filing, NOT at the bankruptcy date. Report the distribution of (event_date − last_filing_date) in quarters.
2. Label each firm-quarter t with four horizon targets y_h (h = 1..4): y_h = 1 if the firm's bankruptcy event occurs within h quarters after t. Survivors get all zeros. Firm-quarters after a firm's event are excluded entirely.
3. Build sequences: sliding window of 8 quarters, stride 1, per firm, requiring ≥ 6 of 8 quarters non-null per feature on average (document the exact completeness rule chosen). Forward-fill within firm for gaps ≤ 2 quarters before windowing; never fill across the event date.
4. Chronological split by the window's END quarter: train ≤ 2019Q4, val 2020Q1–2021Q4, test 2022Q1–2024Q4. No firm-quarter may appear in two splits; a window whose quarters straddle a boundary belongs to the split of its end quarter.
5. Z-score normalisation parameters fit on train only, saved to `data/processed/scaler_params.json`, applied to all splits. Do NOT apply SMOTE/Focal-Loss-related resampling here — that belongs to the modelling stage.

Outputs: `data/processed/sequences_{train,val,test}.npz` (X: [n, 8, 29], y: [n, 4], plus firm/quarter index arrays) and `data/processed/split_manifest.csv`.

**Gate — leakage audit, written to `reports/leakage_audit.md`:** prove (with code output, not assertion) that (a) no firm-quarter index appears in two splits, (b) scaler and winsorisation params derive only from train-period data, (c) no window contains quarters after its firm's event date, (d) max quarter in train < min label horizon quarter in val.

## Phase 6 — Supplementary datasets (quick)

Download the UCI Taiwanese and Polish bankruptcy datasets and the Kaggle US bankruptcy dataset (if `kaggle` CLI is not configured, write the download instructions into the README and skip — do not block). Store under `data/external/` with a small loader script each. No processing beyond load-and-describe.

## Phase 7 — Final deliverables

- `reports/DATASET_REPORT.md`: firm counts, positive counts per split and per horizon, sequence counts, class rates, coverage summary, all known caveats (interest-expense fallback rate, sentinel counts, YTD-differencing stats, unmatched positives).
- Completed `README.md`: environment setup, exact reproduction commands, data dictionary for every output file.
- `docs/DECISIONS.md`: every judgment call you made, with one-line rationale.
- The full-run time/disk estimate for the `--full` flag.

## Acceptance criteria (all must pass before you declare done)

1. `run_all.py` (or `make all`) reproduces everything from an empty `data/` except the LoPucki file, on the pilot universe, without manual intervention.
2. ≥ 250 labelled bankrupt firms; every one either appears in the panel or is listed in `unmatched_positives.csv` with a reason.
3. Sequences exist for all three splits; positive rate per split is reported and non-zero in each; test-set positives ≥ 20.
4. Leakage audit passes all four checks with printed evidence.
5. Hand-recomputation spot-check in Phase 4 matches.
6. Coverage, ratios, labels, and dataset reports all exist and contain real numbers, not placeholders.
7. All unit tests pass, including both YTD filer-style fixtures.

Work through the phases in order, announce each phase as you start it, show each gate's evidence when you pass it, and keep going until all seven criteria are met.
