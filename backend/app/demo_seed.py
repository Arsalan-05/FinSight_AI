"""Inline starter data when demo@finsight.ai clone is unavailable."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from db.models import Account, Transaction, User
from scripts.canadian_demo import prior_month_transactions

logger = logging.getLogger(__name__)


def provision_starter_data(db: Session, user: User) -> bool:
    """Create Canadian student demo accounts + transactions directly for this user."""
    checking = Account(
        user_id=user.id,
        name="RBC Student Chequing",
        institution="RBC",
        account_type="checking",
    )
    credit = Account(
        user_id=user.id,
        name="Simplii Cash Back Visa",
        institution="Simplii Financial",
        account_type="credit",
    )
    db.add_all([checking, credit])
    db.flush()

    extras = [
        Transaction(
            account_id=checking.id,
            transaction_date=date(2026, 6, 1),
            description="Co-op Paycheque",
            amount=2800.00,
            category="Income",
            merchant="Employer",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 2),
            description="Loblaws Groceries",
            amount=-94.20,
            category="Groceries",
            merchant="Loblaws",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 3),
            description="INTERAC E-TRANSFER SENT - RENT",
            amount=-950.00,
            category="Housing",
            merchant="Landlord",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 8),
            description="TTC Presto Load",
            amount=-156.00,
            category="Transport",
            merchant="TTC",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=date(2026, 6, 12),
            description="Spotify Premium",
            amount=-11.99,
            category="Subscriptions",
            merchant="Spotify",
        ),
    ]
    txs = prior_month_transactions(checking.id, credit.id) + extras
    db.add_all(txs)
    db.commit()
    logger.info("Provisioned %d starter transactions for %s", len(txs), user.email)
    return True
