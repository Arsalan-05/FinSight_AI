"""Evaluation metrics for Phase 1 harness (no LLM dependency)."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Sequence

# Currency-like amounts: $12.34, CAD 12.34, 12.34 CAD, plain 1,234.56 with $ nearby
_CURRENCY_RE = re.compile(
    r"(?:"
    r"\$\s*-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
    r"|\$\s*-?\d+(?:\.\d{1,2})?"
    r"|(?:CAD|USD|C\$)\s*-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
    r"|-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s*(?:CAD|USD)"
    r")",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    text = re.sub(r"(?i)^(cad|usd|c\$)\s*", "", text)
    text = re.sub(r"(?i)\s*(cad|usd)$", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def numeric_match(
    predicted: Any,
    expected: Any,
    *,
    tolerance: float = 0.01,
) -> bool:
    """True when |predicted - expected| <= tolerance (absolute dollars)."""
    p = _to_float(predicted)
    e = _to_float(expected)
    if p is None or e is None:
        return False
    return abs(p - e) <= float(tolerance)


def tool_selection_accuracy(
    predicted_tools: Sequence[str] | None,
    expected_tools: Sequence[str] | None,
) -> dict[str, Any]:
    """Exact set match + partial (Jaccard) tool-selection scores."""
    pred = {t for t in (predicted_tools or []) if t}
    exp = {t for t in (expected_tools or []) if t}
    exact = pred == exp
    if not pred and not exp:
        jaccard = 1.0
    elif not pred or not exp:
        jaccard = 0.0
    else:
        jaccard = len(pred & exp) / len(pred | exp)
    return {
        "exact": exact,
        "partial": jaccard,
        "predicted": sorted(pred),
        "expected": sorted(exp),
    }


def extract_currency_amounts(text: str) -> list[float]:
    """Pull currency-like numbers from free text."""
    if not text:
        return []
    found: list[float] = []
    for match in _CURRENCY_RE.finditer(text):
        val = _to_float(match.group(0))
        if val is not None:
            found.append(val)
    return found


def _tool_json_amounts(tool_outputs: Iterable[str] | None) -> set[float]:
    """Flatten currency/number tokens from tool JSON string blobs."""
    amounts: set[float] = set()
    for blob in tool_outputs or []:
        if blob is None:
            continue
        text = blob if isinstance(blob, str) else str(blob)
        for match in _CURRENCY_RE.finditer(text):
            val = _to_float(match.group(0))
            if val is not None:
                amounts.add(round(val, 2))
        # Also harvest plain JSON numeric fields (amount, total, etc.)
        for match in _NUMBER_RE.finditer(text):
            raw = match.group(0).replace(",", "")
            try:
                amounts.add(round(float(raw), 2))
            except ValueError:
                continue
    return amounts


def hallucinated_number_rate(
    answer: str,
    tool_output_json_strings: Sequence[str] | None,
    *,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Fraction of currency amounts in ``answer`` absent from tool JSON strings.

    An answer amount is grounded if some tool amount is within ``tolerance``.
    """
    answer_amounts = extract_currency_amounts(answer or "")
    if not answer_amounts:
        return {
            "rate": 0.0,
            "hallucinated": [],
            "grounded": [],
            "answer_amounts": [],
            "tool_amounts": sorted(_tool_json_amounts(tool_output_json_strings)),
        }

    tool_amounts = _tool_json_amounts(tool_output_json_strings)
    hallucinated: list[float] = []
    grounded: list[float] = []
    for amt in answer_amounts:
        ok = any(abs(amt - t) <= tolerance for t in tool_amounts)
        if ok:
            grounded.append(amt)
        else:
            hallucinated.append(amt)

    rate = len(hallucinated) / len(answer_amounts)
    return {
        "rate": rate,
        "hallucinated": hallucinated,
        "grounded": grounded,
        "answer_amounts": answer_amounts,
        "tool_amounts": sorted(tool_amounts),
    }


def recall_at_k(
    relevant_ids: Sequence[str],
    ranked_ids: Sequence[str],
    k: int,
) -> float:
    """Recall@k for a single query."""
    relevant = {r for r in relevant_ids if r}
    if not relevant:
        return 0.0
    top = ranked_ids[:k]
    hits = sum(1 for rid in top if rid in relevant)
    return hits / len(relevant)


def mrr(
    relevant_ids: Sequence[str],
    ranked_ids: Sequence[str],
) -> float:
    """Mean Reciprocal Rank for a single query (1/rank of first relevant)."""
    relevant = {r for r in relevant_ids if r}
    if not relevant:
        return 0.0
    for idx, rid in enumerate(ranked_ids, start=1):
        if rid in relevant:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(
    relevant_ids: Sequence[str],
    ranked_ids: Sequence[str],
    k: int,
) -> float:
    """nDCG@k with binary relevance."""
    relevant = {r for r in relevant_ids if r}
    if not relevant or k <= 0:
        return 0.0

    def _dcg(rels: Sequence[float]) -> float:
        total = 0.0
        for i, rel in enumerate(rels, start=1):
            total += rel / math.log2(i + 1)
        return total

    gains = [1.0 if rid in relevant else 0.0 for rid in ranked_ids[:k]]
    ideal_len = min(len(relevant), k)
    ideal = [1.0] * ideal_len + [0.0] * (k - ideal_len)
    ideal_dcg = _dcg(ideal[:k])
    if ideal_dcg == 0.0:
        return 0.0
    return _dcg(gains) / ideal_dcg


def refusal_accuracy(
    *,
    should_refuse: bool,
    did_refuse: bool,
) -> bool:
    """True when the model's refuse/allow decision matches the label."""
    return bool(should_refuse) == bool(did_refuse)


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
