"""Duplicate charge detector — same merchant, same amount, within 72 hours."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set


def _merchant_key(tx: Any) -> str:
    merchant = (getattr(tx, "merchant", None) or "").strip().lower()
    if merchant:
        return merchant
    desc = (getattr(tx, "description", "") or "").strip().lower()
    return desc[:40]


def _amount_key(tx: Any) -> float:
    return round(abs(float(getattr(tx, "amount", 0) or 0)), 2)


def _as_datetime(tx: Any) -> datetime:
    d = getattr(tx, "transaction_date")
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day)


def detect_duplicates(
    transactions: Sequence[Any],
    *,
    recurring_merchants: Optional[Sequence[str]] = None,
    window_hours: int = 72,
) -> List[Dict[str, Any]]:
    """
    Flag pairs with same merchant + same amount within `window_hours`.

    Merchants in `recurring_merchants` (case-insensitive) are excluded.
    Confidence rises when amounts match exactly and the gap is smaller.
    """
    exclude: Set[str] = {m.strip().lower() for m in (recurring_merchants or []) if m}
    debits = [
        tx
        for tx in transactions
        if float(getattr(tx, "amount", 0) or 0) < 0 and _merchant_key(tx)
    ]
    debits.sort(key=lambda t: (_merchant_key(t), _as_datetime(t), _amount_key(t)))

    findings: List[Dict[str, Any]] = []
    seen_pairs: Set[frozenset] = set()
    window = timedelta(hours=window_hours)

    for i, a in enumerate(debits):
        key_a = _merchant_key(a)
        if key_a in exclude:
            continue
        amt_a = _amount_key(a)
        time_a = _as_datetime(a)

        for b in debits[i + 1 :]:
            key_b = _merchant_key(b)
            if key_b != key_a:
                break  # sorted by merchant — stop inner loop for this merchant
            if key_b in exclude:
                continue
            amt_b = _amount_key(b)
            if amt_b != amt_a:
                continue
            time_b = _as_datetime(b)
            gap = abs(time_b - time_a)
            if gap > window:
                continue
            if gap == timedelta(0) and getattr(a, "id", None) == getattr(b, "id", None):
                continue

            pair_ids = frozenset({getattr(a, "id", id(a)), getattr(b, "id", id(b))})
            if pair_ids in seen_pairs:
                continue
            seen_pairs.add(pair_ids)

            # Confidence: exact amount (already) + tighter window → higher score
            hours = gap.total_seconds() / 3600.0
            # 0h → 0.95, 24h → ~0.85, 72h → ~0.70
            confidence = round(max(0.55, 0.95 - (hours / window_hours) * 0.25), 2)

            amount = amt_a
            findings.append(
                {
                    "type": "duplicate",
                    "amount_cad": amount,
                    "status": "open",
                    "title": f"Possible duplicate at {_display_merchant(a)}",
                    "message": (
                        f"Two charges of ${amount:.2f} within {hours:.0f}h "
                        f"(confidence {confidence:.0%})."
                    ),
                    "evidence": {
                        "merchant": _display_merchant(a),
                        "amount": amount,
                        "hours_apart": round(hours, 1),
                        "confidence": confidence,
                        "transaction_ids": [
                            getattr(a, "id", None),
                            getattr(b, "id", None),
                        ],
                        "dates": [
                            getattr(a, "transaction_date").isoformat(),
                            getattr(b, "transaction_date").isoformat(),
                        ],
                        "descriptions": [
                            getattr(a, "description", ""),
                            getattr(b, "description", ""),
                        ],
                    },
                    "fingerprint": "duplicate:"
                    + ":".join(sorted(str(x) for x in pair_ids)),
                }
            )

    findings.sort(key=lambda f: f["evidence"]["confidence"], reverse=True)
    return findings


def _display_merchant(tx: Any) -> str:
    return (getattr(tx, "merchant", None) or getattr(tx, "description", "")[:40] or "Unknown").strip()
