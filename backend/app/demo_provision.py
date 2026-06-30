"""Clone demo data or create inline starter data for new OAuth users."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.demo_seed import provision_starter_data
from db.models import Account, Transaction, TransactionEmbedding, User

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@finsight.ai"


def ensure_user_has_data(db: Session, user: User) -> bool:
    """Ensure the user has accounts and transactions (clone demo or inline seed)."""
    if db.query(Account).filter(Account.user_id == user.id).count() > 0:
        return False
    if _clone_from_demo_user(db, user):
        return True
    return provision_starter_data(db, user)


def provision_demo_if_empty(db: Session, user: User) -> bool:
    """Backward-compatible alias."""
    return ensure_user_has_data(db, user)


def _clone_from_demo_user(db: Session, user: User) -> bool:
    demo = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not demo or demo.id == user.id:
        return False

    demo_accounts = db.query(Account).filter(Account.user_id == demo.id).all()
    if not demo_accounts:
        return False

    account_map: dict[str, str] = {}
    for acc in demo_accounts:
        clone = Account(
            user_id=user.id,
            name=acc.name,
            institution=acc.institution,
            account_type=acc.account_type,
        )
        db.add(clone)
        db.flush()
        account_map[acc.id] = clone.id

    tx_count = 0
    for old_acc_id, new_acc_id in account_map.items():
        for tx in db.query(Transaction).filter(Transaction.account_id == old_acc_id).all():
            new_tx = Transaction(
                account_id=new_acc_id,
                transaction_date=tx.transaction_date,
                description=tx.description,
                amount=tx.amount,
                category=tx.category,
                merchant=tx.merchant,
                notes=tx.notes,
            )
            db.add(new_tx)
            db.flush()
            tx_count += 1

            emb = (
                db.query(TransactionEmbedding)
                .filter(TransactionEmbedding.transaction_id == tx.id)
                .first()
            )
            if emb:
                db.add(
                    TransactionEmbedding(
                        transaction_id=new_tx.id,
                        content=emb.content,
                        embedding=emb.embedding,
                    )
                )

    db.commit()
    logger.info("Cloned %d transactions for user %s", tx_count, user.email)
    return True
