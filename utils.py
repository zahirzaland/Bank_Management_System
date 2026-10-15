"""Small shared helpers: money, dates, timestamps."""
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple

import config
from exceptions import ValidationError

_MONEY_RE = re.compile(r"\d+(\.\d{1,%d})?" % config.DECIMAL_PLACES)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def parse_money(text, field: str = "Amount") -> int:
    """Convert user text such as '1,234.50' to integer minor units, exactly."""
    raw = str(text or "").strip().replace(",", "")
    if raw.startswith(config.CURRENCY_SYMBOL):
        raw = raw[len(config.CURRENCY_SYMBOL):].strip()
    if not _MONEY_RE.fullmatch(raw):
        raise ValidationError(
            f"{field} must be a number with at most {config.DECIMAL_PLACES} decimal places (e.g. 250.00)."
        )
    return int(Decimal(raw) * config.MINOR_UNITS_PER_MAJOR)


def plain_money(minor: int) -> str:
    """Plain decimal text without symbol or separators (used in reports/CSV)."""
    sign = "-" if minor < 0 else ""
    major, frac = divmod(abs(int(minor)), config.MINOR_UNITS_PER_MAJOR)
    return f"{sign}{major}.{frac:0{config.DECIMAL_PLACES}d}"


def format_money(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    major, frac = divmod(abs(int(minor)), config.MINOR_UNITS_PER_MAJOR)
    return f"{sign}{config.CURRENCY_SYMBOL}{major:,}.{frac:0{config.DECIMAL_PLACES}d}"


def parse_date(text, field: str = "Date") -> Optional[date]:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field} must use the format YYYY-MM-DD.") from None


def day_bounds(date_from: Optional[date], date_to: Optional[date]) -> Tuple[Optional[str], Optional[str]]:
    """Return [start, end) timestamp strings; end is exclusive (start of the next day)."""
    if date_from and date_to and date_from > date_to:
        raise ValidationError("'From' date must not be later than 'To' date.")
    start = f"{date_from:%Y-%m-%d} 00:00:00" if date_from else None
    end = f"{date_to + timedelta(days=1):%Y-%m-%d} 00:00:00" if date_to else None
    return start, end


def escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
