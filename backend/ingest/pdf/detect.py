"""Detect Canadian bank from statement text."""

from __future__ import annotations

import re

_BANK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("rbc", re.compile(r"\b(?:rbc|royal\s+bank(?:\s+of\s+canada)?)\b", re.I)),
    ("td", re.compile(r"\b(?:td\s+canada\s+trust|td\s+bank|toronto[\s-]?dominion)\b", re.I)),
    ("scotiabank", re.compile(r"\b(?:scotiabank|bank\s+of\s+nova\s+scotia)\b", re.I)),
    ("bmo", re.compile(r"\b(?:bmo|bank\s+of\s+montreal)\b", re.I)),
    ("cibc", re.compile(r"\bcibc\b", re.I)),
    ("tangerine", re.compile(r"\btangerine\b", re.I)),
    ("simplii", re.compile(r"\bsimplii\b", re.I)),
    ("eq", re.compile(r"\beq\s+bank\b", re.I)),
]


def detect_bank(text: str) -> str:
    """Return a bank id from statement text, or ``unknown``."""
    if not text or not text.strip():
        return "unknown"
    for bank_id, pattern in _BANK_PATTERNS:
        if pattern.search(text):
            return bank_id
    return "unknown"
