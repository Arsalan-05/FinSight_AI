"""Normalize raw merchant strings from POS / PayPal / Square descriptors."""

from __future__ import annotations

import re

# Processor / marketplace prefixes
_PREFIXES = re.compile(
    r"^\s*(?:"
    r"SQ\s*\*?\s*"
    r"|TST\s*\*?\s*"
    r"|PAYPAL\s*\*?\s*"
    r"|PP\s*\*?\s*"
    r"|SP\s*\*?\s*"
    r"|GOOGLE\s*\*?\s*"
    r"|CHECKCARD\s+"
    r"|POS\s+"
    r"|PURCHASE\s+"
    r"|DEBIT\s+"
    r")",
    re.I,
)

# Trailing store / location noise
_STORE_NUMBER = re.compile(
    r"\s+#?\d{2,6}\s*$"  # #1234 or 12345 at end
    r"|\s+STORE\s*#?\s*\d+\b"
    r"|\s+#\d+\b",
    re.I,
)
_CITY_PROVINCE = re.compile(
    r"\s+[A-Z][A-Za-z.\-]*(?:\s+[A-Z][A-Za-z.\-]*){0,2}\s+"
    r"(?:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU|CA|US)\s*$"
)
_TRAILING_CITY = re.compile(
    r"\s+(?:TORONTO|VANCOUVER|MONTREAL|CALGARY|OTTAWA|EDMONTON|"
    r"MISSISSAUGA|BRAMPTON|WINNIPEG|HAMILTON|QUEBEC|HALIFAX|"
    r"LONDON|KITCHENER|VICTORIA|SASKATOON|REGINA)\s*$",
    re.I,
)
_MULTI_SPACE = re.compile(r"\s+")
_NON_ALNUM_EDGE = re.compile(r"^[\s*#\-_.]+|[\s*#\-_.]+$")


def normalize_merchant(raw: str | None) -> str | None:
    """Strip processor prefixes, store numbers, and city suffixes.

    Returns ``None`` for empty input; otherwise a cleaned display name.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    # Repeatedly strip known prefixes (SQ* SQ* …)
    for _ in range(3):
        cleaned = _PREFIXES.sub("", text)
        if cleaned == text:
            break
        text = cleaned.strip()

    text = _STORE_NUMBER.sub("", text)
    text = _CITY_PROVINCE.sub("", text)
    text = _TRAILING_CITY.sub("", text)
    text = _NON_ALNUM_EDGE.sub("", text)
    text = _MULTI_SPACE.sub(" ", text).strip()

    if not text:
        return None
    return text[:120]
