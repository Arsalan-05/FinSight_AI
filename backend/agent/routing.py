"""Heuristic model router: cheap 8B vs stronger 70B."""

from __future__ import annotations

import re

# Multi-step / planning / comparison signals → 70B
_HEAVY_PATTERNS = (
    r"\bwhat[\s-]?if\b",
    r"\bplan\b",
    r"\bplanning\b",
    r"\btfsa\b",
    r"\brrsp\b",
    r"\bfhsa\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bversus\b",
    r"\bvs\.?\b",
    r"\bscenario\b",
    r"\bforecast\b",
    r"\bproject(?:ion|ed)?\b",
    r"\boptimiz(?:e|ation)\b",
    r"\bmulti[\s-]?step\b",
    r"\bshould i\b",
    r"\btrade[\s-]?off\b",
)

_HEAVY_RE = re.compile("|".join(_HEAVY_PATTERNS), re.IGNORECASE)


def route_model(question: str) -> str:
    """Return ``\"8b\"`` or ``\"70b\"`` based on question complexity heuristics."""
    text = (question or "").strip()
    if not text:
        return "8b"
    if _HEAVY_RE.search(text):
        return "70b"
    return "8b"
