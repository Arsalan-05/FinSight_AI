"""Load the eval persona fixture into a SQLAlchemy session."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from db.models import Account, Transaction, User
from evals.fixtures.seed_persona import (
    ACCOUNT_RBC,
    ACCOUNT_TD,
    build_fixture_transactions,
)


def load_fixture_into_db(
    db: Session,
    user_email: str = "eval@finsight.local",
) -> dict[str, Any]:
    """Create eval user + RBC/TD accounts + ~600 transactions.

    Idempotent for the given email: if the user already exists, their accounts
    and transactions are wiped and re-seeded so the fixture stays frozen.

    Returns a dict with user, accounts, transaction count, and planted_leaks.
    """
    existing = db.query(User).filter(User.email == user_email).one_or_none()
    if existing is not None:
        account_ids = [a.id for a in db.query(Account).filter(Account.user_id == existing.id)]
        if account_ids:
            db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).delete(
                synchronize_session=False
            )
            db.query(Account).filter(Account.user_id == existing.id).delete(
                synchronize_session=False
            )
        user = existing
        user.name = "Eval Persona"
    else:
        user = User(email=user_email, name="Eval Persona")
        db.add(user)
        db.flush()

    rbc = Account(
        user_id=user.id,
        name="RBC Student Chequing",
        institution="RBC",
        account_type="checking",
    )
    td = Account(
        user_id=user.id,
        name="TD Cash Back Visa",
        institution="TD",
        account_type="credit",
    )
    db.add_all([rbc, td])
    db.flush()

    account_ids = {
        ACCOUNT_RBC: rbc.id,
        ACCOUNT_TD: td.id,
        "checking": rbc.id,
        "credit": td.id,
    }
    rows, planted_leaks = build_fixture_transactions(user.id, account_ids)

    orm_txs = [
        Transaction(
            id=row["id"],
            account_id=row["account_id"],
            transaction_date=row["transaction_date"],
            description=row["description"],
            amount=row["amount"],
            category=row["category"],
            merchant=row["merchant"],
            notes=row["notes"],
        )
        for row in rows
    ]
    db.add_all(orm_txs)
    db.commit()

    return {
        "user": user,
        "user_id": user.id,
        "email": user_email,
        "accounts": {
            ACCOUNT_RBC: rbc,
            ACCOUNT_TD: td,
        },
        "account_ids": {
            ACCOUNT_RBC: rbc.id,
            ACCOUNT_TD: td.id,
        },
        "transaction_count": len(orm_txs),
        "transactions": orm_txs,
        "planted_leaks": planted_leaks,
    }
