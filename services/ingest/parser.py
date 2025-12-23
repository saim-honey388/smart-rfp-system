"""Parse structured fields from proposal text (simple heuristics)."""

import re
from datetime import datetime
from typing import Optional, Dict, Tuple, List


_PRICE_PATTERN = re.compile(r"(?P<currency>usd|eur|gbp|\$|€|£)?\s?(?P<amount>\d[\d,\.]{2,})", re.IGNORECASE)
_DATE_PATTERN = re.compile(
    r"(?P<date>(\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4})|(\d{1,2} \w+ \d{4}))",
    re.IGNORECASE,
)


def parse_price(text: str) -> Tuple[Optional[float], Optional[str]]:
    match = _PRICE_PATTERN.search(text)
    if not match:
        return None, None
    raw = match.group("amount").replace(",", "")
    try:
        amount = float(raw)
    except ValueError:
        return None, None
    currency = match.group("currency") or None
    currency = currency.upper() if currency and len(currency) > 1 else currency
    return amount, currency


def _coerce_date(raw: str) -> Optional[str]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_dates(text: str) -> Dict[str, Optional[str]]:
    match = _DATE_PATTERN.search(text)
    if not match:
        return {"start_date": None}
    raw = match.group("date")
    parsed = _coerce_date(raw)
    return {"start_date": parsed}


def extract_emails(text: str) -> List[str]:
    """Return a list of email addresses found in the text."""
    pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    return pattern.findall(text)

