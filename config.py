from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Need 2015 data so 2016-01 can have valid 3M and 6M momentum signals.
START_DATE = "2015-01-01"
BACKTEST_START = "2016-01-01"

# Strategy grid: keep the original project format.
MOMENTUM_WINDOWS = [6, 3]
TOP_NS = [1, 2, 3]
HOLDING_MONTHS = [1, 2, 3]

WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

CURRENT_TICKERS_FILE = DATA_DIR / "nasdaq100_current_tickers.csv"
COMPONENT_CHANGES_FILE = DATA_DIR / "nasdaq100_component_changes.csv"
ALL_HISTORICAL_TICKERS_FILE = DATA_DIR / "nasdaq100_all_historical_tickers.csv"
PRICE_FILE = DATA_DIR / "nasdaq100_prices.csv"

# Backward-compatible alias for older scripts/users.
TICKER_FILE = CURRENT_TICKERS_FILE

SIX_MONTH_DETAIL_FILE = OUTPUT_DIR / "six_month_detail.csv"
THREE_MONTH_DETAIL_FILE = OUTPUT_DIR / "three_month_detail.csv"
SIX_MONTH_SUMMARY_FILE = OUTPUT_DIR / "six_month_summary.csv"
THREE_MONTH_SUMMARY_FILE = OUTPUT_DIR / "three_month_summary.csv"

README_FILE = PROJECT_ROOT / "README.md"
