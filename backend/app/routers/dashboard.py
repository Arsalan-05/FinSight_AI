"""Single-payload dashboard endpoint — one round-trip for Overview first paint."""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@router.get("")
@router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Everything the Overview page needs in one response."""
    empty: dict[str, Any] = {
        "provisioned_demo": False,
        "accounts": [],
        "recent": [],
        "kpis": {
            "cur_spend": 0.0,
            "cur_income": 0.0,
            "prev_spend": 0.0,
            "net_savings": 0.0,
            "spend_change_pct": None,
            "credit_count": 0,
        },
        "top_categories": [],
        "daily": [],
        "insight_cards": [],
        "weekly_brief": None,
    }
    try:
        return _build_dashboard(db, current_user)
    except Exception:
        logger.exception("GET /dashboard failed")
        # Prefer a degraded payload over a hard 500 for Overview first paint.
        try:
            accounts = accounts_for_user(db, current_user)
            empty["accounts"] = [
                account_to_out(db, a).model_dump(mode="json") for a in accounts
            ]
        except Exception:
            logger.exception("dashboard account fallback failed")
        return empty


def _build_dashboard(db: Session, current_user: User | None) -> dict[str, Any]:
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

    cur_spend_q = base.filter(
        Transaction.transaction_date >= cur_start,
        Transaction.transaction_date <= cur_end,
        Transaction.amount < 0,
    )
    cur_income_q = base.filter(
        Transaction.transaction_date >= cur_start,
        Transaction.transaction_date <= cur_end,
        Transaction.amount > 0,
    )
    prev_spend_q = base.filter(
        Transaction.transaction_date >= prev_start,
        Transaction.transaction_date <= prev_end,
        Transaction.amount < 0,
    )

    cur_spend = abs(_f(cur_spend_q.with_entities(func.sum(Transaction.amount)).scalar()))
    cur_income = _f(cur_income_q.with_entities(func.sum(Transaction.amount)).scalar())
    credit_count = int(cur_income_q.with_entities(func.count()).scalar() or 0)
    prev_spend = abs(_f(prev_spend_q.with_entities(func.sum(Transaction.amount)).scalar()))
    net_savings = cur_income - cur_spend
    spend_change_pct = (
        ((cur_spend - prev_spend) / prev_spend) * 100 if prev_spend > 0 else None
    )

    cat_rows = (
        cur_spend_q.with_entities(Transaction.category, func.sum(Transaction.amount))
        .group_by(Transaction.category)
        .all()
    )
    top_categories = sorted(
        [
            {"category": c or "Uncategorized", "amount": round(abs(_f(total)), 2)}
            for c, total in cat_rows
        ],
        key=lambda x: x["amount"],
        reverse=True,
    )[:6]

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
        {"day": d.isoformat()[5:], "spend": round(abs(_f(total)), 2)}
        for d, total in daily_rows
    ]

    insight_cards: list[dict[str, Any]] = []
    weekly_brief: dict[str, Any] | None = None
    if accounts:
        try:
            insights = build_all_insights(db, account_ids=account_ids)
            insight_cards = list(insights.get("insight_cards") or [])
        except Exception:
            logger.exception("dashboard insights failed")
            insight_cards = []
        try:
            weekly_brief = build_weekly_brief(db, account_ids=account_ids)
        except Exception:
            logger.exception("dashboard weekly brief failed")
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
            "spend_change_pct": (
                round(spend_change_pct, 1) if spend_change_pct is not None else None
            ),
            "credit_count": credit_count,
        },
        "top_categories": top_categories,
        "daily": daily,
        "insight_cards": insight_cards,
        "weekly_brief": weekly_brief,
    }
