"""Account list helpers with Plaid sync metadata."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import AccountOut
from db.models import Account, BankConnection


def account_to_out(db: Session, account: Account) -> AccountOut:
    last_synced = None
    if account.bank_connection_id:
        conn = db.get(BankConnection, account.bank_connection_id)
        if conn:
            last_synced = conn.last_synced_at
    return AccountOut(
        id=account.id,
        user_id=account.user_id,
        name=account.name,
        institution=account.institution,
        account_type=account.account_type,
        created_at=account.created_at,
        plaid_linked=bool(account.plaid_account_id),
        last_synced_at=last_synced,
    )
