from __future__ import annotations

from datetime import date
from typing import Any, Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Transaction

GroupBy = Literal["category", "merchant", "month", "none"]
TransactionType = Literal["all", "debit", "credit"]


def aggregate_spending(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    group_by: GroupBy = "category",
    category: str | None = None,
    account_id: str | None = None,
    account_ids: list[str] | None = None,
    transaction_type: TransactionType = "all",
) -> dict[str, Any]:
    """Run SQL aggregates over transactions and return a JSON-serializable summary."""
    q = db.query(Transaction)

    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    elif account_ids is not None:
        if not account_ids:
            empty: dict[str, Any] = {
                "group_by": group_by,
                "count": 0,
                "total": 0.0,
                "filters": _filters_dict(
                    start_date, end_date, account_id, transaction_type, category
                ),
            }
            if group_by != "none":
                empty["groups"] = []
            return empty
        q = q.filter(Transaction.account_id.in_(account_ids))
    if category:
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    if start_date:
        q = q.filter(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(Transaction.transaction_date <= end_date)
    if transaction_type == "debit":
        q = q.filter(Transaction.amount < 0)
    elif transaction_type == "credit":
        q = q.filter(Transaction.amount > 0)

    if group_by == "none":
        row = q.with_entities(
            func.count(Transaction.id).label("tx_count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        ).one()
        return {
            "group_by": "none",
            "count": int(row.tx_count),
            "total": round(float(row.total), 2),
            "filters": _filters_dict(start_date, end_date, account_id, transaction_type, category),
        }

    label_key: str
    group_col: Any
    if group_by == "category":
        group_col = Transaction.category
        label_key = "category"
    elif group_by == "merchant":
        group_col = Transaction.merchant
        label_key = "merchant"
    else:
        group_col = _month_group_expr(db)
        label_key = "month"

    rows = (
        q.with_entities(
            group_col.label("label"),
            func.count(Transaction.id).label("tx_count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .group_by(group_col)
        .order_by(func.sum(Transaction.amount))
        .all()
    )

    groups = [
        {
            label_key: row.label or "Unknown",
            "count": int(row.tx_count),
            "total": round(float(row.total), 2),
        }
        for row in rows
    ]

    return {
        "group_by": group_by,
        "groups": groups,
        "filters": _filters_dict(start_date, end_date, account_id, transaction_type, category),
    }


def _month_group_expr(db: Session) -> Any:
    """Dialect-aware YYYY-MM expression for grouping by month."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        return func.strftime("%Y-%m", Transaction.transaction_date)
    return func.to_char(Transaction.transaction_date, "YYYY-MM")


def _filters_dict(
    start_date: date | None,
    end_date: date | None,
    account_id: str | None,
    transaction_type: str,
    category: str | None = None,
) -> dict[str, str | None]:
    return {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "account_id": account_id,
        "transaction_type": transaction_type,
        "category": category,
    }
