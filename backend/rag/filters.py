"""Parse structured date/amount filters from a natural-language search query."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass
class QueryFilters:
    """Structured filters extracted before vector/keyword search."""

    date_from: date | None = None
    date_to: date | None = None
    amount_min: float | None = None
    amount_max: float | None = None
    amount_exact: float | None = None
    cleaned_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "amount_min": self.amount_min,
            "amount_max": self.amount_max,
            "amount_exact": self.amount_exact,
            "cleaned_query": self.cleaned_query,
        }

    @property
    def has_filters(self) -> bool:
        return any(
            v is not None
            for v in (
                self.date_from,
                self.date_to,
                self.amount_min,
                self.amount_max,
                self.amount_exact,
            )
        )


_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_MONTH_YEAR = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|"
    r"november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\s+(\d{4})\b",
    re.I,
)
_LAST_N_DAYS = re.compile(r"\blast\s+(\d+)\s+days?\b", re.I)
_LAST_MONTH = re.compile(r"\blast\s+month\b", re.I)
_THIS_MONTH = re.compile(r"\bthis\s+month\b", re.I)
_IN_YEAR = re.compile(r"\bin\s+(\d{4})\b", re.I)
_AMOUNT_EXACT = re.compile(
    r"(?:\$|cad\s*)?(\d+(?:\.\d{1,2})?)\s*(?:dollars?)?\b"
    r"|\b(?:exactly|of)\s+\$?(\d+(?:\.\d{1,2})?)\b",
    re.I,
)
_AMOUNT_OVER = re.compile(r"\b(?:over|above|more\s+than|greater\s+than)\s+\$?(\d+(?:\.\d{1,2})?)", re.I)
_AMOUNT_UNDER = re.compile(
    r"\b(?:under|below|less\s+than|fewer\s+than)\s+\$?(\d+(?:\.\d{1,2})?)", re.I
)
_AMOUNT_BETWEEN = re.compile(
    r"\bbetween\s+\$?(\d+(?:\.\d{1,2})?)\s+and\s+\$?(\d+(?:\.\d{1,2})?)",
    re.I,
)

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def parse_query_filters(query: str, *, today: date | None = None) -> QueryFilters:
    """Extract date/amount constraints and return a cleaned residual query string."""
    today = today or date.today()
    text = query or ""
    cleaned = text
    date_from: date | None = None
    date_to: date | None = None
    amount_min: float | None = None
    amount_max: float | None = None
    amount_exact: float | None = None

    # Date ranges (order matters — consume matched spans from cleaned)
    if m := _LAST_N_DAYS.search(cleaned):
        n = int(m.group(1))
        date_from = today - timedelta(days=n)
        date_to = today
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _LAST_MONTH.search(cleaned):
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        date_from = last_prev.replace(day=1)
        date_to = last_prev
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _THIS_MONTH.search(cleaned):
        date_from = today.replace(day=1)
        date_to = today
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _MONTH_YEAR.search(cleaned):
        month = _MONTHS[m.group(1).lower()]
        year = int(m.group(2))
        date_from, date_to = _month_bounds(year, month)
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _IN_YEAR.search(cleaned):
        year = int(m.group(1))
        date_from, date_to = date(year, 1, 1), date(year, 12, 31)
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]

    iso_dates = list(_ISO_DATE.finditer(cleaned))
    if len(iso_dates) >= 2:
        d1 = date.fromisoformat(iso_dates[0].group(1))
        d2 = date.fromisoformat(iso_dates[1].group(1))
        date_from, date_to = min(d1, d2), max(d1, d2)
        # Remove both matches (from end so offsets stay valid)
        for m in reversed(iso_dates[:2]):
            cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif len(iso_dates) == 1 and date_from is None:
        d = date.fromisoformat(iso_dates[0].group(1))
        date_from = date_to = d
        m = iso_dates[0]
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]

    if m := _AMOUNT_BETWEEN.search(cleaned):
        a, b = float(m.group(1)), float(m.group(2))
        amount_min, amount_max = min(a, b), max(a, b)
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _AMOUNT_OVER.search(cleaned):
        amount_min = float(m.group(1))
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := _AMOUNT_UNDER.search(cleaned):
        amount_max = float(m.group(1))
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    elif m := re.search(r"\$(\d+(?:\.\d{1,2})?)", cleaned):
        # Bare "$12.99" → exact abs amount match hint
        amount_exact = float(m.group(1))
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    return QueryFilters(
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        amount_exact=amount_exact,
        cleaned_query=cleaned or text.strip(),
    )
