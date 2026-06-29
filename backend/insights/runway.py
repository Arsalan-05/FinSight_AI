"""Irregular income / student co-op cash runway analyzer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from db.models import Transaction


def analyze_cash_runway(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    monthly_burn_override: float | None = None,
) -> dict[str, Any]:
    """Estimate months of runway from recent spending patterns."""
    since = date.today() - timedelta(days=90)
    q = db.query(Transaction).filter(Transaction.transaction_date >= since)
    if account_ids is not None:
        if not account_ids:
            return {"runway_months": 0, "message": "No accounts to analyze."}
        q = q.filter(Transaction.account_id.in_(account_ids))

    txs = q.all()
    debits = [abs(float(t.amount)) for t in txs if float(t.amount) < 0]
    credits = [float(t.amount) for t in txs if float(t.amount) > 0]

    if not debits:
        return {"runway_months": None, "message": "Not enough spending history."}

    days = max(1, (date.today() - since).days)
    monthly_burn = monthly_burn_override or (sum(debits) / days) * 30
    monthly_income = (sum(credits) / days) * 30 if credits else 0
    net_monthly = monthly_income - monthly_burn

    # Rough liquid estimate from net credits minus debits in period
    liquid_estimate = sum(credits) + sum(-d for d in debits)  # net in 90d window
    runway = liquid_estimate / monthly_burn if monthly_burn > 0 else None

    return {
        "monthly_burn": round(monthly_burn, 2),
        "monthly_income_estimate": round(monthly_income, 2),
        "net_monthly": round(net_monthly, 2),
        "runway_months": round(runway, 1) if runway is not None else None,
        "message": (
            f"Based on 90-day history: ~${monthly_burn:,.0f}/mo burn, "
            f"~${monthly_income:,.0f}/mo income. "
            + (
                f"Estimated runway: {runway:.1f} months at current burn."
                if runway is not None
                else "Insufficient data for runway."
            )
        ),
    }
