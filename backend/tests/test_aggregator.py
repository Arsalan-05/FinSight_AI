"""Unit tests for the spending aggregator SQL tool."""

from __future__ import annotations

from datetime import date

from agent.tools.aggregator import aggregate_spending
from db.models import Account, Transaction, User


def _seed_transactions(db_session) -> str:
    user = User(email="agg@test.com", name="Agg User")
    db_session.add(user)
    db_session.flush()

    account = Account(
        user_id=user.id,
        name="Checking",
        institution="Chase",
        account_type="checking",
    )
    db_session.add(account)
    db_session.flush()

    txs = [
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 1),
            description="Coffee",
            amount=-5.50,
            category="Dining",
            merchant="Starbucks",
        ),
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 10),
            description="Groceries",
            amount=-80.00,
            category="Groceries",
            merchant="Whole Foods",
        ),
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 15),
            description="Salary",
            amount=3000.00,
            category="Income",
            merchant="Employer",
        ),
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 6, 1),
            description="Dinner",
            amount=-45.00,
            category="Dining",
            merchant="Olive Garden",
        ),
    ]
    db_session.add_all(txs)
    db_session.commit()
    return account.id


class TestAggregateSpending:
    def test_group_by_category(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(db_session, group_by="category")

        assert result["group_by"] == "category"
        categories = {g["category"]: g["total"] for g in result["groups"]}
        assert categories["Dining"] == -50.50
        assert categories["Groceries"] == -80.00
        assert categories["Income"] == 3000.00

    def test_filter_debits_only(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(db_session, group_by="none", transaction_type="debit")

        assert result["count"] == 3
        assert result["total"] == -130.50

    def test_filter_credits_only(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(db_session, group_by="none", transaction_type="credit")

        assert result["count"] == 1
        assert result["total"] == 3000.00

    def test_date_range_filter(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(
            db_session,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            group_by="none",
        )

        assert result["count"] == 1
        assert result["total"] == -45.00

    def test_group_by_month(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(db_session, group_by="month")

        months = {g["month"]: g["total"] for g in result["groups"]}
        assert "2026-05" in months
        assert "2026-06" in months

    def test_group_by_merchant(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(db_session, group_by="merchant")

        merchants = {g["merchant"]: g["total"] for g in result["groups"]}
        assert merchants["Starbucks"] == -5.50
        assert merchants["Employer"] == 3000.00

    def test_account_filter(self, db_session) -> None:
        account_id = _seed_transactions(db_session)
        result = aggregate_spending(db_session, account_id=account_id, group_by="none")

        assert result["count"] == 4

    def test_filter_by_category(self, db_session) -> None:
        _seed_transactions(db_session)
        result = aggregate_spending(
            db_session,
            group_by="none",
            category="Dining",
            transaction_type="debit",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )
        assert result["count"] == 1
        assert result["total"] == -5.50

    def test_empty_result(self, db_session) -> None:
        result = aggregate_spending(db_session, group_by="none")
        assert result["count"] == 0
        assert result["total"] == 0.0
