# Bankruptcy-prediction dataset pipeline.
#
# `make all` reproduces every artefact from an empty data/ except the LoPucki
# Cases table, which must be downloaded by hand (see README).
#
# On Windows, run these through Git Bash, or use the equivalent
# `python run_all.py ...` commands directly.

PY := .venv/Scripts/python.exe
ifeq ($(OS),)
PY := .venv/bin/python
endif

.PHONY: all venv download labels universe fundamentals ratios sequences \
        external reports test clean clean-derived full-estimate

all: test
	$(PY) run_all.py

venv:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

download:            ## Phase 0: SEC bulk files (~3.0 GB, cached)
	$(PY) src/download_bulk.py

labels: download     ## Phase 1: 8-K item 1.03 sweep + LoPucki cross-check
	$(PY) src/scan_submissions.py
	$(PY) src/phase1_labels.py

universe: labels     ## Phase 2: non-financial universe + seeded pilot sample
	$(PY) src/phase2_universe.py

fundamentals: universe   ## Phase 3: XBRL extraction with YTD de-cumulation
	$(PY) src/phase3_fundamentals.py

ratios: fundamentals ## Phase 4: 28 ratios + negative-equity flag, then the gate
	$(PY) src/phase4_ratios.py
	$(PY) src/verify_ratios.py

sequences: ratios    ## Phase 5: labels, 8-quarter windows, split, leakage audit
	$(PY) src/phase5_sequences.py

external:            ## Phase 6: UCI Taiwanese + Polish (Kaggle is manual)
	$(PY) src/phase6_external.py

reports: sequences external   ## Phase 7: dataset report + full-run estimate
	$(PY) src/phase7_report.py
	$(PY) src/estimate_full_run.py

full-estimate:
	$(PY) src/estimate_full_run.py

test:
	$(PY) -m pytest tests/ -q

clean-derived:       ## drop everything regenerable, keep the big downloads
	rm -rf data/interim data/processed data/universe_pilot.csv
	rm -f reports/*.md reports/*.csv

clean: clean-derived ## also drop the cached downloads
	rm -rf data/raw/cache data/raw/companyfacts.zip data/raw/submissions.zip \
	       data/raw/company_tickers.json data/raw/bulk_manifest.json
