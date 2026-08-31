"""Central configuration: paths, SEC etiquette, XBRL tag chains, window/split spec.

Every magic value used by more than one phase lives here so the pipeline has a
single source of truth. Tag chains are transcribed from
`Dataset_Sources_and_Ratio_Derivability_Summary.md` section 3; entries marked
ADDED are documented extensions logged in docs/DECISIONS.md.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"
CACHE = RAW / "cache"

for _p in (RAW, INTERIM, PROCESSED, EXTERNAL, DOCS, REPORTS, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# SEC etiquette
# --------------------------------------------------------------------------
SEC_CONTACT_NAME = "Aakaash Limaye"
SEC_CONTACT_EMAIL = os.environ.get("SEC_EMAIL", "aakaashdevendra.limaye01@nmims.in")
USER_AGENT = f"{SEC_CONTACT_NAME} {SEC_CONTACT_EMAIL} MPSTME capstone research"
SEC_MAX_RPS = 8.0          # SEC allows 10/s; we stay under it.
SEC_TIMEOUT = 120
SEC_RETRIES = 5

BULK_COMPANYFACTS_URL = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
BULK_SUBMISSIONS_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

# --------------------------------------------------------------------------
# Study window / splits  (Capstone Summary section 6)
# --------------------------------------------------------------------------
STUDY_START = "2010-01-01"
STUDY_END = "2024-12-31"
LABEL_SWEEP_YEARS = list(range(2009, 2026))   # one year of margin either side

WINDOW_LEN = 8                 # quarters per sequence
WINDOW_STRIDE = 1
HORIZONS = (1, 2, 3, 4)        # y_h for h = 1..4
MIN_NONNULL_QUARTERS = 6       # >= 6 of 8 quarters non-null per feature, on average
MAX_FFILL_GAP = 2              # forward-fill gaps of at most 2 quarters within firm

TRAIN_END = "2019Q4"           # train <= 2019Q4 (also winsorise/scaler fitting period)
VAL_START, VAL_END = "2020Q1", "2021Q4"
TEST_START, TEST_END = "2022Q1", "2024Q4"
TRAIN_CUTOFF_DATE = "2019-12-31"

PILOT_TARGET_FIRMS = 500
RANDOM_SEED = 42

# SIC codes to exclude: financials, insurance, real estate
SIC_EXCLUDE_LO, SIC_EXCLUDE_HI = 6000, 6799

# Duration-span windows (days) used by the YTD de-cumulation logic
QUARTER_SPAN = (80, 100)
SEMI_SPAN = (170, 200)
NINE_MONTH_SPAN = (260, 290)
ANNUAL_SPAN = (350, 380)

ACCEPTED_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A",
                  "10-KT", "10-QT", "10-KT/A", "10-QT/A"}

# --------------------------------------------------------------------------
# XBRL tag fallback chains
# --------------------------------------------------------------------------
# kind: "instant" (balance sheet, point-in-time) or "duration" (flow, needs
# YTD de-cumulation). Chains are tried left to right; the first tag supplying a
# value for a given firm-quarter wins and is recorded in the provenance column.
CONCEPTS: dict[str, dict] = {
    # ---- instants (balance sheet) ----------------------------------------
    "Assets":                {"kind": "instant", "tags": ["Assets"]},
    "AssetsCurrent":         {"kind": "instant", "tags": ["AssetsCurrent"]},
    "Liabilities":           {"kind": "instant", "tags": ["Liabilities"]},
    # ADDED: enables the derived Liabilities fallback (L&SE - Equity)
    "LiabilitiesAndStockholdersEquity": {"kind": "instant",
                                         "tags": ["LiabilitiesAndStockholdersEquity"]},
    "LiabilitiesCurrent":    {"kind": "instant", "tags": ["LiabilitiesCurrent"]},
    "StockholdersEquity":    {"kind": "instant", "tags": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]},
    # ADDED: same tags as StockholdersEquity but NCI-inclusive first, so the
    # derived Liabilities fallback (L&SE - equity) does not overstate by NCI.
    "StockholdersEquityInclNCI": {"kind": "instant", "tags": [
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity",
    ]},
    "CashAndEquivalents":    {"kind": "instant", "tags": [
        "CashAndCashEquivalentsAtCarryingValue",
    ]},
    "InventoryNet":          {"kind": "instant", "tags": ["InventoryNet"]},
    "AccountsReceivable":    {"kind": "instant", "tags": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",                            # ADDED
        "AccountsReceivableNet",                            # ADDED (same concept)
        "AccountsReceivableGrossCurrent",                   # ADDED
    ]},
    "AccountsPayable":       {"kind": "instant", "tags": [
        "AccountsPayableCurrent",
        "AccountsPayableTradeCurrent",                      # ADDED
    ]},
    "RetainedEarnings":      {"kind": "instant", "tags": [
        "RetainedEarningsAccumulatedDeficit",
    ]},
    "LongTermDebtNoncurrent": {"kind": "instant", "tags": [
        "LongTermDebtNoncurrent", "LongTermDebt",
    ]},
    "LongTermDebtCurrent":   {"kind": "instant", "tags": [
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",    # ADDED
    ]},
    "ShortTermBorrowings":   {"kind": "instant", "tags": [
        "ShortTermBorrowings",
        "CommercialPaper",
        "NotesPayableCurrent",
        "OtherShortTermBorrowings",                         # ADDED
    ]},
    "DebtCurrent":           {"kind": "instant", "tags": ["DebtCurrent"]},

    # ---- durations (flows) ------------------------------------------------
    "Revenue":               {"kind": "duration", "tags": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",                             # ADDED
        "SalesRevenueServicesNet",                          # ADDED
        # ADDED: industry-specific top lines found by scanning pilot firms that
        # report Assets but no tag from the generic chain (oil & gas, utilities)
        "RegulatedAndUnregulatedOperatingRevenue",
        "OilAndGasRevenue",
        "OilAndGasSalesRevenue",
        "NaturalGasProductionRevenue",
    ]},
    "COGS":                  {"kind": "duration", "tags": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfServices",
    ]},
    "OperatingIncomeLoss":   {"kind": "duration", "tags": ["OperatingIncomeLoss"]},
    "NetIncomeLoss":         {"kind": "duration", "tags": [
        "NetIncomeLoss",
        "ProfitLoss",                                       # ADDED
        "NetIncomeLossAvailableToCommonStockholdersBasic",  # ADDED
    ]},
    "InterestExpense":       {"kind": "duration", "tags": [
        "InterestExpense",
        "InterestExpenseDebt",                              # ADDED (named in spec prose)
        "InterestExpenseNonoperating",                      # ADDED (2021+ successor tag)
        "InterestAndDebtExpense",                           # ADDED
    ]},
    "IncomeTaxExpenseBenefit": {"kind": "duration", "tags": ["IncomeTaxExpenseBenefit"]},
    "DepreciationAmortization": {"kind": "duration", "tags": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",          # ADDED
        "Depreciation",
    ]},
    "AmortizationOfIntangibleAssets": {"kind": "duration", "tags": [
        "AmortizationOfIntangibleAssets",
    ]},
    "OCF":                   {"kind": "duration", "tags": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",   # ADDED
    ]},
    "CapEx":                 {"kind": "duration", "tags": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",                # ADDED
        "PaymentsForCapitalImprovements",                   # ADDED
    ]},
}

# Concepts the Phase-3 coverage gate calls "Tier 1" (expect >= 90% non-null)
TIER1_CONCEPTS = [
    "Assets", "AssetsCurrent", "LiabilitiesCurrent", "Liabilities",
    "StockholdersEquity", "NetIncomeLoss", "CashAndEquivalents",
    "RetainedEarnings",
]

# Flat set of XBRL tags to pull out of companyfacts (for fast filtering)
ALL_TAGS = sorted({t for c in CONCEPTS.values() for t in c["tags"]})

RATIO_NAMES = [
    "r01_current_ratio", "r02_quick_ratio", "r03_cash_ratio", "r04_wc_to_ta",
    "r05_net_profit_margin", "r06_roa", "r07_roe", "r08_ebitda_margin",
    "r09_ebit_to_ta", "r10_re_to_ta",
    "r11_debt_to_equity", "r12_debt_to_assets", "r13_interest_coverage",
    "r14_equity_to_liabilities", "r15_ltd_to_ta",
    "r16_asset_turnover", "r17_inventory_turnover", "r18_receivables_turnover",
    "r19_payables_turnover", "r20_cash_conversion_cycle",
    "r21_revenue_growth", "r22_net_income_growth", "r23_assets_growth",
    "r24_equity_growth",
    "r25_ocf_to_cl", "r26_fcf_to_ta", "r27_accrual_quality", "r28_ocf_to_debt",
    "r29_negative_equity_flag",
]
assert len(RATIO_NAMES) == 29

# Ratios that are structurally undefined (not missing) for firms without
# inventory / without debt. Handled with NaN + an indicator column.
INVENTORY_RATIOS = ["r02_quick_ratio", "r17_inventory_turnover",
                    "r20_cash_conversion_cycle"]
DEBT_RATIOS = ["r13_interest_coverage"]

# Indicator columns carried alongside the 29 features
INDICATOR_NAMES = ["has_inventory", "has_debt"]

# r29 is a 0/1 flag; winsorising it would be meaningless
NO_WINSORISE = {"r29_negative_equity_flag"}


# --------------------------------------------------------------------------
# Pilot vs full-run artefact paths
# --------------------------------------------------------------------------
def suffix(full: bool) -> str:
    """Full-universe runs write to their own files so pilot outputs survive."""
    return "_full" if full else ""


def panel_path(full: bool = False):
    return INTERIM / f"fundamentals_panel{suffix(full)}.parquet"


def ratios_path(full: bool = False):
    return PROCESSED / f"ratios_panel{suffix(full)}.parquet"


def chunk_dir(full: bool = False):
    return INTERIM / f"_fund_chunks{suffix(full)}"
