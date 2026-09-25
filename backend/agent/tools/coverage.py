from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Transaction


def transaction_date_span(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    category: str | None = None,
) -> dict[str, str | None]:
    """Earliest/latest transaction dates in scope (for empty-result guidance)."""
    q = db.query(
        func.min(Transaction.transaction_date),
        func.max(Transaction.transaction_date),
    )
    if account_ids is not None:
        if not account_ids:
            return {"earliest": None, "latest": None}
        q = q.filter(Transaction.account_id.in_(account_ids))
    if category:
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    earliest, latest = q.one()
    return {
        "earliest": earliest.isoformat() if earliest else None,
        "latest": latest.isoformat() if latest else None,
    }


def latest_month_with_spend(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    category: str | None = None,
    transaction_type: str = "debit",
) -> tuple[date, date] | None:
    """Calendar month of the most recent matching spend, or None."""
    q = db.query(func.max(Transaction.transaction_date))
    if account_ids is not None:
        if not account_ids:
            return None
        q = q.filter(Transaction.account_id.in_(account_ids))
    if category:
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    if transaction_type == "debit":
        q = q.filter(Transaction.amount < 0)
    elif transaction_type == "credit":
        q = q.filter(Transaction.amount > 0)
    latest = q.scalar()
    if latest is None:
        return None
    if isinstance(latest, str):
        latest = date.fromisoformat(latest)
    first = latest.replace(day=1)
    # end of that month
    if first.month == 12:
        end = date(first.year, 12, 31)
    else:
        end = date(first.year, first.month + 1, 1)
        from datetime import timedelta

        end = end - timedelta(days=1)
    return first, end


def attach_coverage(
    result: dict[str, Any],
    db: Session,
    *,
    account_ids: list[str] | None,
    category: str | None,
) -> dict[str, Any]:
    """Annotate aggregate result with available data span for the model."""
    span = transaction_date_span(db, account_ids=account_ids, category=None)
    cat_span = (
        transaction_date_span(db, account_ids=account_ids, category=category)
        if category
        else span
    )
    result["data_coverage"] = {
        "all_transactions": span,
        "matching_category": cat_span if category else None,
    }
    return result
