# Phase 6 - Supplementary External Datasets

Loaded and described only, per the spec; no processing beyond this.
Each has a loader in `src/phase6_external.py`

| Dataset | Loader |
|---|---|
| UCI Taiwanese | `load_taiwanese()` |
| UCI Polish | `load_polish()` -> dict of 5 frames |
| Kaggle US | `load_kaggle_us()` |

### UCI Taiwanese Bankruptcy Prediction

- rows: **6,819**, columns: **96**
- label column: `Bankrupt?`
- positives: **220** (3.23%), negatives: 6,599
- numeric columns: 96
- cells missing: 0.000%
- first columns: Bankrupt?,  ROA(C) before interest and depreciation before interest,  ROA(A) before interest and % after tax,  ROA(B) before interest and depreciation after tax,  Operating Gross Margin,  Realized Sales Gross Margin

### UCI Polish Companies Bankruptcy

Five files, one per years-before-bankruptcy horizon:

| File | Rows | Cols | Positives | Positive rate | Missing cells |
|---|---:|---:|---:|---:|---:|
| `1year` | 7,027 | 65 | 271 | 3.86% | 1.28% |
| `2year` | 10,173 | 65 | 400 | 3.93% | 1.84% |
| `3year` | 10,503 | 65 | 495 | 4.71% | 1.45% |
| `4year` | 9,792 | 65 | 515 | 5.26% | 1.38% |
| `5year` | 5,910 | 65 | 410 | 6.94% | 1.21% |

### Kaggle - US Company Bankruptcy Prediction Dataset

Not downloaded automatically: Kaggle requires an authenticated API token, and
the pipeline takes no credentials. To add it:

1. Create a free account at https://www.kaggle.com and go to
   *Settings -> API -> Create New Token*. This downloads `kaggle.json`.
2. Place it at `%USERPROFILE%\.kaggle\kaggle.json` (Windows) or
   `~/.kaggle/kaggle.json` (Linux/macOS), then `chmod 600` it on POSIX.
3. Install and download:

```bash
pip install kaggle && kaggle datasets download -d utkarshx27/american-companies-bankruptcy-prediction-dataset -p data/external/kaggle_us --unzip
```

4. Re-run `python src/phase6_external.py`, which will pick up any CSV found
   under `data/external/kaggle_us/` and describe it alongside the others.

