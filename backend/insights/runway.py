"""Irregular income / student co-op cash runway analyzer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Account, Transaction

WINDOW_DAYS = 90
# Money moved between the user's own accounts is neither spending nor income.
_INTERNAL_CATEGORIES = ("Savings",)
_CASH_ACCOUNT_TYPES = ("checking", "savings")


def _cash_on_hand(db: Session, account_ids: list[str] | None) -> float:
    """Net of every transaction ever recorded on chequing/savings accounts."""
    q = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Account, Account.id == Transaction.account_id)
        .filter(Account.account_type.in_(_CASH_ACCOUNT_TYPES))
    )
    if account_ids is not None:
        q = q.filter(Transaction.account_id.in_(account_ids))
    return float(q.scalar() or 0)


def analyze_cash_runway(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    monthly_burn_override: float | None = None,
) -> dict[str, Any]:
    """Months until cash runs out if the last 90 days of income and spending continue."""
    since = date.today() - timedelta(days=WINDOW_DAYS)
    q = db.query(Transaction).filter(
        Transaction.transaction_date >= since,
        Transaction.category.notin_(_INTERNAL_CATEGORIES),
    )
    if account_ids is not None:
        if not account_ids:
            return {"runway_months": 0, "message": "No accounts to analyze."}
        q = q.filter(Transaction.account_id.in_(account_ids))

    txs = q.all()
    debits = [abs(float(t.amount)) for t in txs if float(t.amount) < 0]
    credits = [float(t.amount) for t in txs if float(t.amount) > 0]

    if not debits:
        return {"runway_months": None, "message": "Not enough spending history."}

    monthly_burn = monthly_burn_override or sum(debits) / WINDOW_DAYS * 30
    monthly_income = sum(credits) / WINDOW_DAYS * 30
    net_monthly = monthly_income - monthly_burn
    cash_on_hand = _cash_on_hand(db, account_ids)

    summary = f"Last 90 days: ~${monthly_burn:,.0f}/mo spending, ~${monthly_income:,.0f}/mo income."
    runway: float | None
    if net_monthly >= 0:
        runway = None
        message = f"{summary} Income covers spending, so cash is not running down."
    else:
        runway = max(cash_on_hand, 0.0) / -net_monthly
        message = (
            f"{summary} Spending exceeds income by ~${-net_monthly:,.0f}/mo; "
            f"at that pace cash lasts about {runway:.1f} months."
        )

    return {
        "monthly_burn": round(monthly_burn, 2),
        "monthly_income_estimate": round(monthly_income, 2),
        "net_monthly": round(net_monthly, 2),
        "cash_on_hand": round(cash_on_hand, 2),
        "cash_flow_positive": net_monthly >= 0,
        "runway_months": round(runway, 1) if runway is not None else None,
        "message": message,
    }
