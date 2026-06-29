"""Clone Canadian demo data onto OAuth users who have no accounts yet."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from db.models import Account, Transaction, TransactionEmbedding, User

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@finsight.ai"


def provision_demo_if_empty(db: Session, user: User) -> bool:
    """Give a first-time OAuth user the same demo accounts/transactions as demo@finsight.ai."""
    if db.query(Account).filter(Account.user_id == user.id).count() > 0:
        return False

    demo = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not demo or demo.id == user.id:
        logger.warning("Demo seed user missing — run scripts/seed.py first")
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
    logger.info("Provisioned %d transactions for user %s", tx_count, user.email)
    return True
