"""Budget and spend alert notifications."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Account, Budget, Notification, Transaction, User


def _user_prefs(user: User) -> dict[str, Any]:
    try:
        return json.loads(user.alert_prefs_json or "{}")
    except json.JSONDecodeError:
        return {}


def create_notification(
    db: Session,
    *,
    user_id: str,
    title: str,
    body: str,
    severity: str = "warning",
    kind: str = "spend_alert",
) -> Notification:
    note = Notification(
        user_id=user_id,
        kind=kind,
        severity=severity,
        title=title,
        body=body,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def check_budget_alerts(db: Session, user: User) -> list[Notification]:
    """Create in-app notifications when monthly spend exceeds a budget."""
    prefs = _user_prefs(user)
    if not prefs.get("spend_alerts", True):
        return []

    today = date.today()
    month_start = date(today.year, today.month, 1)
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    created: list[Notification] = []

    for budget in budgets:
        spent = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user.id,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= today,
                Transaction.amount < 0,
                Transaction.category.ilike(budget.category),
            )
            .scalar()
        )
        spent_abs = abs(float(spent or 0))
        limit = float(budget.monthly_limit)
        if limit <= 0 or spent_abs < limit:
            continue

        pct = int((spent_abs / limit) * 100)
        title = f"Over budget: {budget.category}"
        body = f"You've spent ${spent_abs:,.0f} of ${limit:,.0f} ({pct}%) this month."
        dup = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.kind == "budget_breach",
                Notification.title == title,
                Notification.read.is_(False),
            )
            .first()
        )
        if dup:
            continue
        created.append(
            create_notification(
                db,
                user_id=user.id,
                title=title,
                body=body,
                kind="budget_breach",
            )
        )
    return created
