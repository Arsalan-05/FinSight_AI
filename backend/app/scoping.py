from __future__ import annotations

from sqlalchemy import false
from sqlalchemy.orm import Query, Session

from db.models import Account, Transaction, User


def accounts_for_user(db: Session, user: User | None) -> list[Account]:
    q = db.query(Account)
    if user is not None:
        q = q.filter(Account.user_id == user.id)
    return q.order_by(Account.created_at.desc()).all()


def account_ids_for_user(db: Session, user: User | None) -> list[str] | None:
    """Return account ids to scope queries, or None when auth is open (dev mode)."""
    if user is None:
        return None
    return [a.id for a in db.query(Account.id).filter(Account.user_id == user.id).all()]


def scope_transactions(q: Query[Transaction], db: Session, user: User | None) -> Query[Transaction]:
    ids = account_ids_for_user(db, user)
    if ids is None:
        return q
    if not ids:
        return q.filter(false())
    return q.filter(Transaction.account_id.in_(ids))


def assert_account_owned(db: Session, account_id: str, user: User | None) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise ValueError("Account not found")
    if user is not None and account.user_id != user.id:
        raise ValueError("Account not found")
    return account
