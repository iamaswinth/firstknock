import re
from datetime import date
import dateparser

_PRESENT_TOKENS = {"present", "current", "now", "ongoing", "till date", "to date"}

_DATEPARSER_SETTINGS = {
    "DATE_ORDER": "MDY",
    "PREFER_DAY_OF_MONTH": "first",
    "RETURN_AS_TIMEZONE_AWARE": False,
}


def normalize_date(raw: str | None) -> str | None:
    if not raw or raw.strip().lower() in _PRESENT_TOKENS:
        return None

    stripped = raw.strip()

    if re.match(r'^\d{4}$', stripped):
        return stripped

    parsed = dateparser.parse(stripped, settings=_DATEPARSER_SETTINGS)
    if parsed is None:
        return None

    return parsed.strftime("%Y-%m")


def date_range_months(start: str | None, end: str | None) -> int:
    if not start:
        return 0

    start_date = _parse_ym(start)
    if start_date is None:
        return 0

    end_date = _parse_ym(end) if end else date.today().replace(day=1)
    if end_date is None:
        end_date = date.today().replace(day=1)

    return max(0, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))


def _parse_ym(ym: str) -> date | None:
    try:
        if re.match(r'^\d{4}-\d{2}$', ym):
            return date(int(ym[:4]), int(ym[5:7]), 1)
        if re.match(r'^\d{4}$', ym):
            return date(int(ym), 1, 1)
    except ValueError:
        pass
    return None
