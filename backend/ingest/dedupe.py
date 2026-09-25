"""Cross-source transaction deduplication via fuzzy date/amount/merchant match."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Sequence

from ingest.merchants import normalize_merchant


@dataclass(frozen=True)
class DedupeMatch:
    left_id: str
    right_id: str
    score: float
    reason: str


def _get(tx: Any, key: str, default: Any = None) -> Any:
    if isinstance(tx, dict):
        return tx.get(key, default)
    return getattr(tx, key, default)


def _tx_id(tx: Any, fallback: str) -> str:
    value = _get(tx, "id")
    return str(value) if value is not None else fallback


def _tx_date(tx: Any) -> date:
    value = _get(tx, "transaction_date") or _get(tx, "date")
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _tx_amount(tx: Any) -> float:
    return round(float(_get(tx, "amount", 0)), 2)


def _tx_merchant(tx: Any) -> str:
    raw = _get(tx, "merchant") or _get(tx, "description") or ""
    return (normalize_merchant(str(raw)) or str(raw)).strip().lower()


def _merchant_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 4 and shorter in longer:
        return True
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.5


def match_score(
    left: Any,
    right: Any,
    *,
    date_window_days: int = 2,
    amount_tolerance: float = 0.01,
) -> tuple[float, str] | None:
    """Return (score, reason) if *left* and *right* look like duplicates."""
    d_left, d_right = _tx_date(left), _tx_date(right)
    if abs((d_left - d_right).days) > date_window_days:
        return None
    a_left, a_right = _tx_amount(left), _tx_amount(right)
    if abs(a_left - a_right) > amount_tolerance:
        return None
    m_left, m_right = _tx_merchant(left), _tx_merchant(right)
    if not _merchant_similar(m_left, m_right):
        return None

    date_score = 1.0 - (abs((d_left - d_right).days) / max(date_window_days, 1)) * 0.2
    merchant_score = 1.0 if m_left == m_right else 0.85
    score = round((date_score + 1.0 + merchant_score) / 3.0, 4)
    reason = (
        f"date±{abs((d_left - d_right).days)}d amount={a_left:.2f} "
        f"merchant~{m_left[:40]!r}/{m_right[:40]!r}"
    )
    return score, reason


def find_duplicates(
    primary: Sequence[Any],
    secondary: Sequence[Any],
    *,
    date_window_days: int = 2,
    amount_tolerance: float = 0.01,
    min_score: float = 0.8,
) -> list[DedupeMatch]:
    """Fuzzy-match transactions across two sources (e.g. Plaid vs CSV)."""
    matches: list[DedupeMatch] = []
    used_right: set[str] = set()

    for i, left in enumerate(primary):
        left_id = _tx_id(left, f"L{i}")
        best: DedupeMatch | None = None
        for j, right in enumerate(secondary):
            right_id = _tx_id(right, f"R{j}")
            if right_id in used_right or left_id == right_id:
                continue
            scored = match_score(
                left,
                right,
                date_window_days=date_window_days,
                amount_tolerance=amount_tolerance,
            )
            if scored is None:
                continue
            score, reason = scored
            if score < min_score:
                continue
            candidate = DedupeMatch(left_id, right_id, score, reason)
            if best is None or candidate.score > best.score:
                best = candidate
        if best is not None:
            used_right.add(best.right_id)
            matches.append(best)

    return matches


def is_duplicate_of(
    candidate: Any,
    existing: Sequence[Any],
    *,
    date_window_days: int = 2,
) -> Any | None:
    """Return the first existing tx that matches *candidate*, else None."""
    for tx in existing:
        scored = match_score(candidate, tx, date_window_days=date_window_days)
        if scored is not None:
            return tx
    return None


__all__ = [
    "DedupeMatch",
    "find_duplicates",
    "is_duplicate_of",
    "match_score",
    "timedelta",
]
