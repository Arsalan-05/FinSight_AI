"""Numeric grounding guardrail — every $ / % must come from tool output."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# Currency: $1,234.56 | CAD 12.30 | 12.30 CAD | €50
_CURRENCY_RE = re.compile(
    r"(?:"
    r"\$\s*([\d,]+(?:\.\d+)?)"
    r"|(?:CAD|USD|EUR|GBP)\s*([\d,]+(?:\.\d+)?)"
    r"|([\d,]+(?:\.\d+)?)\s*(?:CAD|USD|EUR|GBP)"
    r"|€\s*([\d,]+(?:\.\d+)?)"
    r")",
    re.IGNORECASE,
)

# Percentages: 15% | 15.5 %
_PERCENT_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*%")

# Evidence tags: [[$412.30|ev_1]] — extract the dollar amount
_EVIDENCE_TAG_RE = re.compile(
    r"\[\[\s*\$?\s*([\d,]+(?:\.\d+)?)\s*\|\s*ev_\d+\s*\]\]",
    re.IGNORECASE,
)

_UNVERIFIED_NOTICE = (
    "\n\n[Note: Some amounts could not be verified against your data and were removed.]"
)


@dataclass
class VerifyResult:
    ok: bool
    unverified: list[tuple[str, float]] = field(default_factory=list)
    verified: list[tuple[str, float]] = field(default_factory=list)


def _parse_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _round_amount(value: float) -> float:
    return round(float(value), 2)


def extract_amounts(text: str) -> list[tuple[str, float]]:
    """Extract currency and percentage amounts from text as (raw_span, value) pairs."""
    if not text:
        return []

    found: list[tuple[str, float, int, int]] = []

    for match in _EVIDENCE_TAG_RE.finditer(text):
        raw = match.group(0)
        value = _parse_number(match.group(1))
        found.append((raw, value, match.start(), match.end()))

    for match in _CURRENCY_RE.finditer(text):
        # Skip spans already covered by an evidence tag
        if any(start <= match.start() < end for _, _, start, end in found):
            continue
        groups = [g for g in match.groups() if g is not None]
        if not groups:
            continue
        raw = match.group(0)
        value = _parse_number(groups[0])
        found.append((raw, value, match.start(), match.end()))

    for match in _PERCENT_RE.finditer(text):
        if any(start <= match.start() < end for _, _, start, end in found):
            continue
        raw = match.group(0)
        value = _parse_number(match.group(1))
        found.append((raw, value, match.start(), match.end()))

    found.sort(key=lambda item: item[2])
    return [(raw, value) for raw, value, _, _ in found]


def _walk_numbers(obj: Any, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(_round_amount(float(obj)))
        out.add(_round_amount(abs(float(obj))))
        return
    if isinstance(obj, str):
        # Pull embedded currency/percent strings from tool summaries
        for _, value in extract_amounts(obj):
            out.add(_round_amount(value))
            out.add(_round_amount(abs(value)))
        return
    if isinstance(obj, dict):
        for value in obj.values():
            _walk_numbers(value, out)
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            _walk_numbers(item, out)


def amounts_from_tool_outputs(tool_json_strings: Iterable[str]) -> set[float]:
    """Collect numeric values from tool JSON outputs, rounded to 0.01."""
    known: set[float] = set()
    for raw in tool_json_strings:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Prose sources (user question, goals, profile) state amounts without "$".
            for match in _BARE_NUMBER_RE.finditer(str(raw)):
                try:
                    known.add(_round_amount(_parse_number(match.group(0))))
                except ValueError:
                    continue
            continue
        _walk_numbers(data, known)
    return known


_BARE_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Monthly ↔ yearly ↔ weekly conversions the advisor routinely does.
_PERIOD_FACTORS = (2.0, 3.0, 4.0, 4.33, 6.0, 12.0, 26.0, 52.0)

# Cap pairwise checks so a huge tool dump cannot stall the reply.
_MAX_PAIRWISE = 400


def _is_known(value: float, known: set[float], *, whole: bool = False) -> bool:
    rounded = _round_amount(value)
    if rounded in known or _round_amount(abs(rounded)) in known:
        return True
    if whole:
        # "$186" / "~$4,950" are rounded restatements of $186.40 / $4,952.59.
        tolerance = max(1.0, abs(rounded) * 0.005)
        return any(abs(k - rounded) <= tolerance for k in known)
    return False


def _is_simple_derivation(value: float, known: set[float], *, whole: bool = False) -> bool:
    """Allow sum/diff of two known amounts, or a period conversion of one."""
    amounts = sorted(known, key=abs, reverse=True)[:_MAX_PAIRWISE]
    target = _round_amount(abs(value))
    tolerance = max(1.0, target * 0.005) if whole else 0.01
    for a in amounts:
        for f in _PERIOD_FACTORS:
            if abs(abs(a) * f - target) <= tolerance or abs(abs(a) / f - target) <= tolerance:
                return True
    for i, a in enumerate(amounts):
        for b in amounts[i:]:
            for candidate in (a + b, a - b):
                if abs(abs(candidate) - target) <= tolerance:
                    return True
    return False


def _is_ratio(value: float, known: set[float]) -> bool:
    """Percentages like "up 29%" or "71% of your goal" derived from two known amounts."""
    amounts = [a for a in sorted(known, key=abs, reverse=True)[:_MAX_PAIRWISE] if a]
    target = abs(value)
    for a in amounts:
        for b in amounts:
            if a is b:
                continue
            if abs(abs(a) / abs(b) * 100 - target) <= 0.6:
                return True
            if abs(abs(a - b) / abs(b) * 100 - target) <= 0.6:
                return True
    return False


def verify_numeric_grounding(
    answer: str,
    tool_outputs: Iterable[str],
) -> VerifyResult:
    """Check that every $ / % in the answer is grounded in tool output (or a simple sum/diff)."""
    known = amounts_from_tool_outputs(tool_outputs)
    verified: list[tuple[str, float]] = []
    unverified: list[tuple[str, float]] = []

    for raw, value in extract_amounts(answer):
        is_percent = raw.rstrip().endswith("%")
        whole = not is_percent and "." not in raw
        if (
            _is_known(value, known, whole=whole)
            or _is_simple_derivation(value, known, whole=whole)
            or (is_percent and _is_ratio(value, known))
        ):
            verified.append((raw, value))
        else:
            unverified.append((raw, value))

    return VerifyResult(ok=not unverified, unverified=unverified, verified=verified)


def strip_unverified(answer: str, unverified: list[tuple[str, float]]) -> str:
    """Remove unverified amount spans and append a notice."""
    if not unverified:
        return answer

    result = answer
    # Replace longer spans first so nested/overlapping raw strings are stable
    for raw, _ in sorted(unverified, key=lambda item: len(item[0]), reverse=True):
        # Whole-token match only: "$186" must not eat the front of "$186.40" or an evidence tag.
        pattern = re.compile(r"(?<![\w.,$|\[])" + re.escape(raw) + r"(?![\d]|[.,]\d|\s*\|)")
        result = pattern.sub("[unverified]", result)

    cleaned = result.rstrip()
    if _UNVERIFIED_NOTICE.strip() not in cleaned:
        cleaned += _UNVERIFIED_NOTICE
    return cleaned
