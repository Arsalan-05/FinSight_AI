"""TFSA / RRSP contribution awareness (CRA limits for demo year)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from db.models import Transaction

# 2026 CRA limits (update annually)
TFSA_LIMIT_2026 = 7000.0
RRSP_LIMIT_2026 = 32490.0  # max; actual room varies by income


def tfsa_contribution_status(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Estimate TFSA contributions from savings transfers in the year."""
    yr = year or date.today().year
    start = date(yr, 1, 1)
    end = date(yr, 12, 31)

    q = db.query(Transaction).filter(
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
        Transaction.amount > 0,
    )
    if account_ids is not None:
        if not account_ids:
            return _empty_tfsa(yr)
        q = q.filter(Transaction.account_id.in_(account_ids))

    txs = q.all()
    tfsa_keywords = ("tfsa", "tax-free", "tax free savings")
    rrsp_keywords = ("rrsp", "retirement", "rsp ")

    tfsa_total = 0.0
    rrsp_total = 0.0
    for tx in txs:
        blob = f"{tx.description} {tx.category} {tx.merchant or ''}".lower()
        amt = float(tx.amount)
        if any(k in blob for k in tfsa_keywords):
            tfsa_total += amt
        elif any(k in blob for k in rrsp_keywords):
            rrsp_total += amt

    tfsa_remaining = max(0, TFSA_LIMIT_2026 - tfsa_total)
    return {
        "year": yr,
        "tfsa": {
            "limit": TFSA_LIMIT_2026,
            "estimated_contributions": round(tfsa_total, 2),
            "remaining_room": round(tfsa_remaining, 2),
            "note": "Estimated from transactions tagged TFSA/tax-free. Verify with CRA My Account.",
        },
        "rrsp": {
            "max_limit": RRSP_LIMIT_2026,
            "estimated_contributions": round(rrsp_total, 2),
            "note": "Actual RRSP room depends on prior-year income. This is a demo estimate.",
        },
    }


def _empty_tfsa(year: int) -> dict[str, Any]:
    return {
        "year": year,
        "tfsa": {
            "limit": TFSA_LIMIT_2026,
            "estimated_contributions": 0,
            "remaining_room": TFSA_LIMIT_2026,
            "note": "No accounts linked.",
        },
        "rrsp": {"max_limit": RRSP_LIMIT_2026, "estimated_contributions": 0, "note": ""},
    }
