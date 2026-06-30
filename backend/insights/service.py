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
from insights.tfsa import TFSA_LIMIT_2026, tfsa_contribution_status


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


def build_weekly_brief(
    db: Session,
    *,
    account_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Seven-day money brief for the Overview dashboard."""
    today = date.today()
    week_start = today - timedelta(days=7)
    prev_start = today - timedelta(days=14)

    def _spend_between(start: date, end: date) -> float:
        q = db.query(Transaction).filter(
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.amount < 0,
        )
        if account_ids is not None:
            if not account_ids:
                return 0.0
            q = q.filter(Transaction.account_id.in_(account_ids))
        return sum(abs(float(t.amount)) for t in q.all())

    def _income_between(start: date, end: date) -> float:
        q = db.query(Transaction).filter(
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            Transaction.amount > 0,
        )
        if account_ids is not None:
            if not account_ids:
                return 0.0
            q = q.filter(Transaction.account_id.in_(account_ids))
        return sum(float(t.amount) for t in q.all())

    this_spend = _spend_between(week_start, today)
    prev_spend = _spend_between(prev_start, week_start - timedelta(days=1))
    this_income = _income_between(week_start, today)

    spend_delta_pct: float | None = None
    if prev_spend > 0:
        spend_delta_pct = round((this_spend - prev_spend) / prev_spend * 100, 1)

    # Top category this week
    cat_q = db.query(Transaction).filter(
        Transaction.transaction_date >= week_start,
        Transaction.transaction_date <= today,
        Transaction.amount < 0,
    )
    if account_ids is not None and account_ids:
        cat_q = cat_q.filter(Transaction.account_id.in_(account_ids))
    cat_totals: dict[str, float] = {}
    for tx in cat_q.all():
        cat_totals[tx.category] = cat_totals.get(tx.category, 0) + abs(float(tx.amount))
    top_cat = max(cat_totals.items(), key=lambda x: x[1]) if cat_totals else None

    recurring = detect_recurring_charges(db, account_ids=account_ids)
    subs = subscription_summary(recurring)
    runway = analyze_cash_runway(db, account_ids=account_ids)
    tfsa = tfsa_contribution_status(db, account_ids=account_ids)
    anomalies = detect_anomalies(db, account_ids=account_ids)

    if spend_delta_pct is None:
        headline = f"You spent ${this_spend:,.0f} this week."
    elif spend_delta_pct > 5:
        headline = f"Spending is up {abs(spend_delta_pct):.0f}% vs last week (${this_spend:,.0f})."
    elif spend_delta_pct < -5:
        headline = (
            f"Nice — spending is down {abs(spend_delta_pct):.0f}% "
            f"this week (${this_spend:,.0f})."
        )
    else:
        headline = f"Spending held steady at ${this_spend:,.0f} this week."

    sections: list[dict[str, str]] = []
    if this_income > 0:
        sections.append(
            {
                "id": "income",
                "label": "Income",
                "value": f"${this_income:,.0f} credited this week",
            }
        )
    if top_cat:
        sections.append(
            {
                "id": "top-category",
                "label": "Top category",
                "value": f"{top_cat[0]} — ${top_cat[1]:,.0f}",
            }
        )
    if subs["count"] > 0:
        sections.append(
            {
                "id": "subscriptions",
                "label": "Recurring",
                "value": (
                    f"~${subs['estimated_monthly_total']:,.0f}/mo "
                    f"across {subs['count']} charges"
                ),
            }
        )
    if runway.get("runway_months") is not None:
        sections.append(
            {
                "id": "runway",
                "label": "Cash runway",
                "value": runway["message"],
            }
        )
    if tfsa["tfsa"]["remaining_room"] < TFSA_LIMIT_2026:
        sections.append(
            {
                "id": "tfsa",
                "label": "TFSA room",
                "value": (
                    f"${tfsa['tfsa']['remaining_room']:,.0f} remaining "
                    f"of ${tfsa['tfsa']['limit']:,.0f}"
                ),
            }
        )

    alerts: list[dict[str, str]] = []
    if spend_delta_pct is not None and spend_delta_pct > 15:
        alerts.append(
            {
                "id": "spend-spike",
                "severity": "warning",
                "title": "Spending spike",
                "body": (
                    f"Week-over-week spend rose {spend_delta_pct:.0f}%. "
                    "Review dining and shopping."
                ),
            }
        )
    if runway.get("runway_months") is not None and runway["runway_months"] < 3:
        alerts.append(
            {
                "id": "low-runway",
                "severity": "warning",
                "title": "Low cash runway",
                "body": runway["message"],
            }
        )
    for a in anomalies[:2]:
        alerts.append(
            {
                "id": f"anomaly-{a['transaction_id']}",
                "severity": "warning",
                "title": "Unusual charge",
                "body": a["message"],
            }
        )

    return {
        "generated_at": today.isoformat(),
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "headline": headline,
        "this_week_spend": round(this_spend, 2),
        "prev_week_spend": round(prev_spend, 2),
        "spend_change_pct": spend_delta_pct,
        "sections": sections,
        "alerts": alerts,
        "tfsa": tfsa["tfsa"],
        "subscriptions_monthly": subs["estimated_monthly_total"],
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
