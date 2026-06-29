"""Tests for OAuth user demo provisioning."""

from __future__ import annotations

from app.demo_provision import provision_demo_if_empty
from db.models import Account, Transaction, User


def test_provision_clones_demo_data(db_session):
    demo = User(email="demo@finsight.ai", name="Demo")
    oauth_user = User(email="real@gmail.com", name="Real User", auth_id="supabase-uuid-1")
    db_session.add_all([demo, oauth_user])
    db_session.flush()

    checking = Account(
        user_id=demo.id,
        name="RBC Chequing",
        institution="RBC",
        account_type="checking",
    )
    db_session.add(checking)
    db_session.flush()
    db_session.add(
        Transaction(
            account_id=checking.id,
            transaction_date=__import__("datetime").date(2026, 4, 1),
            description="Coffee",
            amount=-5.0,
            category="Dining",
        )
    )
    db_session.commit()

    assert provision_demo_if_empty(db_session, oauth_user) is True
    assert db_session.query(Account).filter(Account.user_id == oauth_user.id).count() == 1
    assert (
        db_session.query(Transaction)
        .join(Account)
        .filter(Account.user_id == oauth_user.id)
        .count()
        == 1
    )

    assert provision_demo_if_empty(db_session, oauth_user) is False
