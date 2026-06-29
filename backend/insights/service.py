"""Aggregate all proactive insights for the dashboard and agent."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from db.models import Transaction
from insights.anomalies import detect_anomalies
from insights.credit_optimizer import credit_card_tips
from insights.reconciliation import reconcile_accounts
from insights.recurring import detect_recurring_charges, subscription_summary
from insights.runway import analyze_cash_runway
from insights.tfsa import tfsa_contribution_status


def build_all_insights(
    db: Session,
    *,
    account_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build the full insights payload for API and dashboard."""
    recurring = detect_recurring_charges(db, account_ids=account_ids)
    subs = subscription_summary(recurring)
    runway = analyze_cash_runway(db, account_ids=account_ids)
    tfsa = tfsa_contribution_status(db, account_ids=account_ids)
    recon = reconcile_accounts(db, account_ids=account_ids)
    anomalies = detect_anomalies(db, account_ids=account_ids)
    credit = credit_card_tips(db, account_ids=account_ids)
    rent = _rent_ratio(db, account_ids=account_ids)

    cards: list[dict[str, Any]] = []

    if subs["count"] > 0:
        cards.append(
            {
                "id": "subscriptions",
                "severity": "info",
                "title": f"{subs['count']} recurring charges",
                "body": f"~${subs['estimated_monthly_total']:,.2f}/mo in subscriptions and bills.",
                "action": "Review in chat: 'What are my subscriptions?'",
            }
        )

    if rent:
        cards.append(rent)

    if runway.get("runway_months") is not None and runway["runway_months"] < 3:
        cards.append(
            {
                "id": "runway",
                "severity": "warning",
                "title": "Low cash runway",
                "body": runway["message"],
                "action": "Ask: 'How can I reduce my monthly burn?'",
            }
        )

    if tfsa["tfsa"]["remaining_room"] < 2000 and tfsa["tfsa"]["estimated_contributions"] > 0:
        cards.append(
            {
                "id": "tfsa",
                "severity": "info",
                "title": "TFSA room running low",
                "body": (
                    f"${tfsa['tfsa']['remaining_room']:,.0f} remaining of "
                    f"${tfsa['tfsa']['limit']:,.0f} limit."
                ),
                "action": "Ask: 'How much TFSA room do I have?'",
            }
        )

    for a in anomalies[:3]:
        cards.append(
            {
                "id": f"anomaly-{a['transaction_id']}",
                "severity": "warning",
                "title": "Unusual spending",
                "body": a["message"],
                "action": None,
            }
        )

    if credit.get("tips"):
        top = credit["tips"][0]
        cards.append(
            {
                "id": "credit-tip",
                "severity": "success",
                "title": "Rewards optimization",
                "body": top["tip"],
                "action": "Ask: 'Which card should I use for groceries?'",
            }
        )

    return {
        "generated_at": date.today().isoformat(),
        "insight_cards": cards[:8],
        "subscriptions": subs,
        "cash_runway": runway,
        "tfsa_rrsp": tfsa,
        "reconciliation": recon,
        "anomalies": anomalies,
        "credit_optimizer": credit,
    }


def _rent_ratio(db: Session, *, account_ids: list[str] | None) -> dict[str, Any] | None:
    since = date.today() - timedelta(days=30)
    q = db.query(Transaction).filter(
        Transaction.transaction_date >= since,
        or_(
            Transaction.category.ilike("%housing%"),
            Transaction.description.ilike("%rent%"),
        ),
    )
    if account_ids is not None:
        if not account_ids:
            return None
        q = q.filter(Transaction.account_id.in_(account_ids))

    rent_txs = q.all()
    rent_total = sum(abs(float(t.amount)) for t in rent_txs if float(t.amount) < 0)
    if rent_total < 100:
        return None

    income_q = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_date >= since,
        Transaction.amount > 0,
    )
    if account_ids is not None:
        income_q = income_q.filter(Transaction.account_id.in_(account_ids))
    income = float(income_q.scalar() or 0)
    if income <= 0:
        return None

    ratio = rent_total / income * 100
    severity = "warning" if ratio > 40 else "info"
    return {
        "id": "rent-ratio",
        "severity": severity,
        "title": f"Rent is {ratio:.0f}% of income",
        "body": (
            f"${rent_total:,.0f} rent vs ${income:,.0f} income this month (GTA benchmark: ~30–45%)."
        ),
        "action": None,
    }
