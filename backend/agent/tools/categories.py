"""Map user/LLM category phrasing to canonical FinSight labels."""

from __future__ import annotations

_INVALID = frozenset({"none", "all", "any", "null", "n/a", ""})

# User language → stored Transaction.category values
_ALIASES: dict[str, str] = {
    "dining": "Dining",
    "restaurant": "Dining",
    "restaurants": "Dining",
    "eating out": "Dining",
    "eat out": "Dining",
    "takeout": "Dining",
    "take-out": "Dining",
    "take out": "Dining",
    "food delivery": "Dining",
    "delivery": "Dining",
    "coffee": "Dining",
    "cafe": "Dining",
    "café": "Dining",
    "fast food": "Dining",
    "uber eats": "Dining",
    "doordash": "Dining",
    "groceries": "Groceries",
    "grocery": "Groceries",
    "supermarket": "Groceries",
    "loblaws": "Groceries",
    "no frills": "Groceries",
    "costco": "Groceries",
    "transport": "Transport",
    "transportation": "Transport",
    "transit": "Transport",
    "gas": "Transport",
    "fuel": "Transport",
    "uber": "Transport",
    "presto": "Transport",
    "subscriptions": "Subscriptions",
    "subscription": "Subscriptions",
    "streaming": "Subscriptions",
    "utilities": "Utilities",
    "utility": "Utilities",
    "hydro": "Utilities",
    "internet": "Utilities",
    "phone": "Utilities",
    "rent": "Rent",
    "housing": "Rent",
    "income": "Income",
    "salary": "Income",
    "payroll": "Income",
    "transfers": "Transfers",
    "transfer": "Transfers",
    "interac": "Transfers",
    "e-transfer": "Transfers",
    "bank fees": "Bank Fees",
    "fees": "Bank Fees",
    "uncategorized": "Uncategorized",
}


def normalize_category(value: object) -> str | None:
    """Drop bogus values and map synonyms to canonical category labels."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID:
        return None
    mapped = _ALIASES.get(text.lower())
    if mapped:
        return mapped
    # Title-case single tokens that already look canonical
    if text[:1].isupper() or " " in text:
        return text
    return text[:1].upper() + text[1:]
