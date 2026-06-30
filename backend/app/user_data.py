"""User data export and full account deletion (GDPR-style)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from db.models import (
    Account,
    BankConnection,
    Budget,
    ChatSession,
    Notification,
    Transaction,
    User,
)
from integrations.plaid_client import plaid_configured, remove_item
from integrations.token_crypto import connection_access_token


def export_user_data(db: Session, user: User) -> dict[str, Any]:
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    txs = (
        db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).all()
        if account_ids
        else []
    )
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).all()
    connections = (
        db.query(BankConnection).filter(BankConnection.user_id == user.id).all()
    )
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "goals": json.loads(user.goals_json or "[]"),
        "alert_preferences": json.loads(user.alert_prefs_json or "{}"),
        "agent_profile": json.loads(user.agent_profile_json or "{}"),
        "category_rules": json.loads(user.category_rules_json or "[]"),
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "institution": a.institution,
                "account_type": a.account_type,
                "plaid_account_id": a.plaid_account_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in accounts
        ],
        "transactions": [
            {
                "id": t.id,
                "account_id": t.account_id,
                "transaction_date": t.transaction_date.isoformat(),
                "description": t.description,
                "amount": float(t.amount),
                "category": t.category,
                "merchant": t.merchant,
                "notes": t.notes,
            }
            for t in txs
        ],
        "bank_connections": [
            {
                "id": c.id,
                "institution_name": c.institution_name,
                "status": c.status,
                "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            }
            for c in connections
        ],
        "budgets": [
            {
                "id": b.id,
                "category": b.category,
                "monthly_limit": float(b.monthly_limit),
            }
            for b in budgets
        ],
        "chat_sessions": [
            {
                "id": s.id,
                "title": s.title,
                "pinned": s.pinned,
                "message_count": len(json.loads(s.messages_json or "[]")),
            }
            for s in sessions
        ],
    }


def delete_user_and_data(db: Session, user: User) -> None:
    """Hard-delete user and all associated financial data."""
    connections = (
        db.query(BankConnection).filter(BankConnection.user_id == user.id).all()
    )
    if plaid_configured():
        for conn in connections:
            if conn.status != "active":
                continue
            try:
                remove_item(connection_access_token(conn))
            except Exception:
                pass

    account_ids = [
        a.id for a in db.query(Account.id).filter(Account.user_id == user.id).all()
    ]
    if account_ids:
        db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).delete(
            synchronize_session=False
        )
    db.query(Account).filter(Account.user_id == user.id).delete(synchronize_session=False)
    db.query(BankConnection).filter(BankConnection.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(ChatSession).filter(ChatSession.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(Notification).filter(Notification.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(Budget).filter(Budget.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
