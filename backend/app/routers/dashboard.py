"""Single-payload dashboard endpoint — one round-trip for Overview first paint."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.account_serializers import account_to_out
from app.auth import get_current_user_optional
from app.demo_provision import ensure_user_has_data
from app.dependencies import get_db
from app.schemas import AccountOut, TransactionOut
from app.scoping import account_ids_for_user, accounts_for_user, scope_transactions
from db.models import Transaction, User
from insights.service import build_all_insights, build_weekly_brief

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _month_bounds(today: date, *, months_ago: int = 0) -> tuple[date, date]:
    y, m = today.year, today.month - months_ago
    while m <= 0:
        m += 12
        y -= 1
    start = date(y, m, 1)
    end = date(y, m, monthrange(y, m)[1])
    return start, end


def _scoped_tx_query(db: Session, user: User | None):
    return scope_transactions(db.query(Transaction), db, user)


@router.get("")
@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Everything the Overview page needs in one response.

    Replaces: bootstrap + accounts + 3–5 transaction list calls + insights + weekly brief.
    Aggregations run in SQL so we do not ship hundreds of raw rows twice.
    """
    provisioned = False
    if current_user is not None:
        provisioned = ensure_user_has_data(db, current_user)
        db.refresh(current_user)

    accounts = accounts_for_user(db, current_user)
    account_outs: list[AccountOut] = [account_to_out(db, a) for a in accounts]
    account_ids = account_ids_for_user(db, current_user)

    today = date.today()
    cur_start, cur_end = _month_bounds(today, months_ago=0)
    prev_start, prev_end = _month_bounds(today, months_ago=1)
    thirty_start = today - timedelta(days=29)

    base = _scoped_tx_query(db, current_user)

    recent_rows = (
        base.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(10)
        .all()
    )

    # Current / previous month spend & income (SQL aggregates — no fat payloads)
    cur_debits = (
        base.filter(
            Transaction.transaction_date >= cur_start,
            Transaction.transaction_date <= cur_end,
            Transaction.amount < 0,
        )
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0), func.count())
        .one()
    )
    cur_credits = (
        base.filter(
            Transaction.transaction_date >= cur_start,
            Transaction.transaction_date <= cur_end,
            Transaction.amount > 0,
        )
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0), func.count())
        .one()
    )
    prev_debits = (
        base.filter(
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date <= prev_end,
            Transaction.amount < 0,
        )
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .scalar()
    )

    cur_spend = abs(float(cur_debits[0] or 0))
    cur_income = float(cur_credits[0] or 0)
    credit_count = int(cur_credits[1] or 0)
    prev_spend = abs(float(prev_debits or 0))
    net_savings = cur_income - cur_spend
    spend_change_pct = (
        ((cur_spend - prev_spend) / prev_spend) * 100 if prev_spend > 0 else None
    )

    # Top categories this month (debits)
    cat_rows = (
        base.filter(
            Transaction.transaction_date >= cur_start,
            Transaction.transaction_date <= cur_end,
            Transaction.amount < 0,
        )
        .with_entities(Transaction.category, func.sum(Transaction.amount))
        .group_by(Transaction.category)
        .all()
    )
    top_categories = sorted(
        [
            {"category": c or "Uncategorized", "amount": round(abs(float(total or 0)), 2)}
            for c, total in cat_rows
        ],
        key=lambda x: x["amount"],
        reverse=True,
    )[:6]

    # Daily spend last 30 days
    daily_rows = (
        base.filter(
            Transaction.transaction_date >= thirty_start,
            Transaction.transaction_date <= today,
            Transaction.amount < 0,
        )
        .with_entities(Transaction.transaction_date, func.sum(Transaction.amount))
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date)
        .all()
    )
    daily = [
        {
            "day": d.isoformat()[5:],  # MM-DD
            "spend": round(abs(float(total or 0)), 2),
        }
        for d, total in daily_rows
    ]

    insight_cards: list[dict[str, Any]] = []
    weekly_brief: dict[str, Any] | None = None
    if accounts:
        try:
            insights = build_all_insights(db, account_ids=account_ids)
            insight_cards = list(insights.get("insight_cards") or [])
        except Exception:
            insight_cards = []
        try:
            weekly_brief = build_weekly_brief(db, account_ids=account_ids)
        except Exception:
            weekly_brief = None

    return {
        "provisioned_demo": provisioned,
        "accounts": [a.model_dump(mode="json") for a in account_outs],
        "recent": [TransactionOut.model_validate(t).model_dump(mode="json") for t in recent_rows],
        "kpis": {
            "cur_spend": round(cur_spend, 2),
            "cur_income": round(cur_income, 2),
            "prev_spend": round(prev_spend, 2),
            "net_savings": round(net_savings, 2),
            "spend_change_pct": round(spend_change_pct, 1) if spend_change_pct is not None else None,
            "credit_count": credit_count,
        },
        "top_categories": top_categories,
        "daily": daily,
        "insight_cards": insight_cards,
        "weekly_brief": weekly_brief,
    }
