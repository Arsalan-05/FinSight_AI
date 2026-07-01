"""Tests for aggregate date resolution and summaries."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

from agent.tools import execute_tool
from agent.tools.dates import resolve_period
from agent.tools.summarize import summarize_aggregate
from db.models import Account, Transaction, User


def test_resolve_period_last_month() -> None:
    start, end = resolve_period("last_month")
    assert start is not None and end is not None
    assert start < end
    assert start.day == 1


def test_summarize_nonempty() -> None:
    text = summarize_aggregate(
        {
            "group_by": "none",
            "count": 3,
            "total": -94.75,
            "filters": {"category": "Dining", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        }
    )
    assert "94.75" in text
    assert "3 transaction" in text


def test_aggregate_retry_when_category_is_none_string(db_session) -> None:
    user = User(email="nonecat@test.com", name="None Cat")
    db_session.add(user)
    db_session.flush()
    account = Account(
        user_id=user.id, name="Checking", institution="Chase", account_type="checking"
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 10),
            description="Groceries",
            amount=-50.0,
            category="Groceries",
        )
    )
    db_session.commit()

    result = json.loads(
        execute_tool(
            "aggregate_spending",
            {"category": "none", "group_by": "category"},
            db=db_session,
        )
    )
    assert len(result.get("groups", [])) >= 1
    assert "50.00" in result["summary"]


def test_aggregate_retry_on_wrong_year(db_session) -> None:
    user = User(email="retry@test.com", name="Retry")
    db_session.add(user)
    db_session.flush()
    account = Account(
        user_id=user.id, name="Checking", institution="Chase", account_type="checking"
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 15),
            description="Dinner",
            amount=-40.0,
            category="Dining",
        )
    )
    db_session.commit()

    # Freeze "today" so last_month retry always targets May 2026
    with patch("agent.tools.dates.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 30)
        mock_date.fromisoformat = date.fromisoformat

        # Model passes wrong year → empty, then auto-retry last month
        result = json.loads(
            execute_tool(
                "aggregate_spending",
                {
                    "category": "Dining",
                    "start_date": "2025-05-01",
                    "end_date": "2025-05-31",
                    "transaction_type": "debit",
                },
                db=db_session,
            )
        )
    assert result["count"] == 1
    assert "40.00" in result["summary"]
    assert result.get("auto_retried") is True
