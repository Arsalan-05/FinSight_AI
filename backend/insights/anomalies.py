"""Spending anomaly detection with context."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from db.models import Transaction


def detect_anomalies(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    lookback_days: int = 90,
) -> list[dict[str, Any]]:
    """Flag unusual transactions: large amounts, new merchants, category spikes."""
    since = date.today() - timedelta(days=lookback_days)
    q = db.query(Transaction).filter(
        Transaction.transaction_date >= since,
        Transaction.amount < 0,
    )
    if account_ids is not None:
        if not account_ids:
            return []
        q = q.filter(Transaction.account_id.in_(account_ids))

    txs = list(q.all())
    if not txs:
        return []

    by_category: dict[str, list[float]] = defaultdict(list)
    known_merchants: set[str] = set()
    for tx in txs:
        by_category[tx.category].append(abs(float(tx.amount)))
        if tx.merchant:
            known_merchants.add(tx.merchant.lower())

    anomalies: list[dict[str, Any]] = []
    for tx in sorted(txs, key=lambda t: t.transaction_date, reverse=True)[:50]:
        amt = abs(float(tx.amount))
        cat_amounts = by_category.get(tx.category, [])
        if len(cat_amounts) >= 3:
            avg = sum(cat_amounts) / len(cat_amounts)
            if amt > avg * 2.5 and amt > 50:
                anomalies.append(
                    {
                        "type": "large_for_category",
                        "transaction_id": tx.id,
                        "date": tx.transaction_date.isoformat(),
                        "description": tx.description,
                        "amount": amt,
                        "category": tx.category,
                        "message": (
                            f"${amt:.2f} is {(amt / avg):.1f}× your usual {tx.category} spend "
                            f"(avg ${avg:.2f})"
                        ),
                    }
                )
                continue

        merchant = (tx.merchant or tx.description[:30]).lower()
        if merchant and merchant not in known_merchants and amt > 30:
            anomalies.append(
                {
                    "type": "new_merchant",
                    "transaction_id": tx.id,
                    "date": tx.transaction_date.isoformat(),
                    "description": tx.description,
                    "amount": amt,
                    "category": tx.category,
                    "message": f"First time at {tx.merchant or tx.description[:40]} — ${amt:.2f}",
                }
            )

    return anomalies[:10]
