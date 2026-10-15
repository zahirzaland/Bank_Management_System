"""Central configuration for the Bank Management System (educational simulation)."""
import os
from pathlib import Path

APP_NAME = "Bank Management System"
APP_SUBTITLE = "Educational simulation - Designed just for improving development"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("BMS_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.environ.get("BMS_DB_PATH", DATA_DIR / "bank.db"))
LOG_PATH = DATA_DIR / "bms.log"
BACKUP_DIR = DATA_DIR / "backups"

# --- Money -----------------------------------------------------------------
# One currency is used consistently. Balances are stored as integer minor units
# (cents) - binary floating point is never used for money.
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"
DECIMAL_PLACES = 2
MINOR_UNITS_PER_MAJOR = 10 ** DECIMAL_PLACES
MAX_AMOUNT_MINOR = 1_000_000_000 * MINOR_UNITS_PER_MAJOR  # 1 billion per operation

# --- Time ------------------------------------------------------------------
# All timestamps are stored and displayed in UTC ("YYYY-MM-DD HH:MM:SS").
TIMEZONE_NAME = "UTC"

# --- Domain ----------------------------------------------------------------
ACCOUNT_TYPES = ("Savings", "Checking", "Fixed Deposit")
ACCOUNT_STATUSES = ("active", "frozen", "closed")
TRANSACTION_TYPES = ("opening", "deposit", "withdrawal", "transfer", "reversal")
ROLES = ("admin", "teller", "viewer")
IDLE_TIMEOUT_SECONDS = 15 * 60
INTEREST_RATES_BPS = {"Savings": 200, "Fixed Deposit": 350}
MAX_LOAN_RATE_BPS = 5000
MAX_LOAN_TERM_MONTHS = 360

# --- Security --------------------------------------------------------------
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt's limit; keeps every supported hasher consistent
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 60

# --- UI --------------------------------------------------------------------
SEARCH_LIMIT = 500
