"""Detect recurring subscription and bill payments."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from db.models import Transaction


def detect_recurring_charges(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    lookback_days: int = 180,
    min_occurrences: int = 2,
) -> list[dict[str, Any]]:
    """Find merchants with repeated similar amounts (subscriptions, bills)."""
    since = date.today() - timedelta(days=lookback_days)
    q = db.query(Transaction).filter(Transaction.transaction_date >= since)
    if account_ids is not None:
        if not account_ids:
            return []
        q = q.filter(Transaction.account_id.in_(account_ids))

    txs = q.order_by(Transaction.transaction_date.desc()).all()

    # Group by normalized merchant or description prefix
    buckets: dict[str, list[Transaction]] = defaultdict(list)
    for tx in txs:
        if float(tx.amount) >= 0:
            continue
        key = (tx.merchant or tx.description[:40]).strip().lower()
        if len(key) < 3:
            continue
        buckets[key].append(tx)

    recurring: list[dict[str, Any]] = []
    for key, group in buckets.items():
        if len(group) < min_occurrences:
            continue
        amounts = [abs(float(t.amount)) for t in group]
        avg = sum(amounts) / len(amounts)
        # Similar amounts within 15%
        if max(amounts) - min(amounts) > avg * 0.15 and avg > 5:
            continue
        latest = max(group, key=lambda t: t.transaction_date)
        monthly_est = avg * (30 / max(1, _median_gap_days(group)))
        recurring.append(
            {
                "merchant": latest.merchant or latest.description,
                "category": latest.category,
                "amount": round(avg, 2),
                "occurrences": len(group),
                "last_date": latest.transaction_date.isoformat(),
                "estimated_monthly": round(min(monthly_est, avg * 4), 2),
                "transaction_ids": [t.id for t in group[:5]],
            }
        )

    recurring.sort(key=lambda x: x["estimated_monthly"], reverse=True)
    return recurring


def _median_gap_days(txs: list[Transaction]) -> int:
    if len(txs) < 2:
        return 30
    dates = sorted(t.transaction_date for t in txs)
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    gaps.sort()
    return gaps[len(gaps) // 2] or 30


def subscription_summary(recurring: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(r["estimated_monthly"] for r in recurring)
    return {
        "count": len(recurring),
        "estimated_monthly_total": round(total, 2),
        "items": recurring[:15],
    }
