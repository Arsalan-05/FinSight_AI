"""Credit card rewards optimization tips based on spend patterns."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Transaction

# Simplified Canadian card reward rules (demo)
_CARD_RULES: dict[str, dict[str, float]] = {
    "scene": {"Groceries": 5, "Dining": 2, "Entertainment": 3, "default": 1},
    "amex_cobalt": {"Dining": 5, "Groceries": 5, "Transit": 2, "default": 1},
    "rbc_avion": {"Travel": 1.25, "Dining": 1, "default": 1},
    "td_cashback": {"Groceries": 3, "Gas": 3, "Recurring": 3, "default": 0.5},
    "simplii_cashback": {"Restaurants": 4, "Groceries": 1.5, "default": 0.5},
}


def credit_card_tips(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    lookback_days: int = 90,
) -> dict[str, Any]:
    """Suggest which card to use per category based on spend volume."""
    since = date.today() - timedelta(days=lookback_days)
    q = (
        db.query(Transaction.category, func.sum(func.abs(Transaction.amount)))
        .filter(Transaction.transaction_date >= since, Transaction.amount < 0)
        .group_by(Transaction.category)
    )
    if account_ids is not None:
        if not account_ids:
            return {"tips": [], "message": "No spending data."}
        q = q.filter(Transaction.account_id.in_(account_ids))

    category_spend = {row[0]: float(row[1]) for row in q.all()}
    if not category_spend:
        return {"tips": [], "message": "No spending data in period."}

    tips: list[dict[str, Any]] = []
    for category, spend in sorted(category_spend.items(), key=lambda x: -x[1])[:8]:
        best_card = None
        best_rate = 0.0
        for card, rules in _CARD_RULES.items():
            rate = rules.get(category, rules.get("default", 0))
            if rate > best_rate:
                best_rate = rate
                best_card = card
        if best_card and spend > 20:
            tips.append(
                {
                    "category": category,
                    "monthly_spend_estimate": round(spend / 3, 2),
                    "recommended_card": best_card.replace("_", " ").title(),
                    "reward_rate_percent": best_rate,
                    "tip": (
                        f"Put {category} (${spend / 3:.0f}/mo avg) on "
                        f"{best_card.replace('_', ' ').title()} for up to {best_rate}% back."
                    ),
                }
            )

    return {
        "tips": tips,
        "message": f"{len(tips)} category optimizations based on last {lookback_days} days.",
        "disclaimer": "Demo rules only — verify current card terms with your issuer.",
    }
