"""Sync Plaid transactions into FinSight accounts."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from db.models import Account, BankConnection, Transaction
from integrations.plaid_client import get_accounts, sync_transactions
from rag.embedder import build_content, embed_texts

logger = logging.getLogger(__name__)


def _embed_transactions(txs: list[Transaction], db: Session) -> None:
    if not settings.embeddings_configured or not txs:
        return
    try:
        from db.models import TransactionEmbedding

        contents = [build_content(tx) for tx in txs]
        vectors = embed_texts(contents, input_type="document")
        for tx, content, vector in zip(txs, contents, vectors):
            db.add(
                TransactionEmbedding(
                    transaction_id=tx.id,
                    content=content,
                    embedding=vector,
                )
            )
        db.commit()
    except Exception:
        logger.exception("Plaid sync: embedding failed")
        db.rollback()


def _map_account_type(plaid_type: str, subtype: str | None) -> str:
    if plaid_type == "credit":
        return "credit"
    if subtype in {"savings", "cd", "money market"}:
        return "savings"
    return "checking"


def _plaid_amount_to_finsight(amount: float, account_type: str) -> float:
    """FinSight: negative = money out. Plaid depository: positive = money out."""
    if account_type == "credit":
        return -abs(amount)
    return -amount


def _ensure_plaid_account(
    db: Session,
    *,
    user_id: str,
    connection: BankConnection,
    plaid_account: dict[str, Any],
) -> Account:
    plaid_id = plaid_account["account_id"]
    existing = (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.plaid_account_id == plaid_id,
        )
        .first()
    )
    if existing:
        return existing

    acct_type = _map_account_type(
        plaid_account.get("type", "depository"),
        plaid_account.get("subtype"),
    )
    name = plaid_account.get("name") or plaid_account.get("official_name") or "Linked account"
    mask = plaid_account.get("mask")
    if mask:
        name = f"{name} ····{mask}"

    account = Account(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        institution=connection.institution_name or "Linked bank",
        account_type=acct_type,
        plaid_account_id=plaid_id,
        bank_connection_id=connection.id,
    )
    db.add(account)
    db.flush()
    return account


def sync_connection(db: Session, connection: BankConnection) -> dict[str, Any]:
    """Pull new/updated transactions for one bank connection."""
    accounts_payload = get_accounts(connection.access_token)
    plaid_accounts = {a["account_id"]: a for a in accounts_payload.get("accounts", [])}

    added_count = 0
    modified_count = 0
    cursor = connection.transactions_cursor or ""
    has_more = True

    new_txs: list[Transaction] = []

    while has_more:
        payload = sync_transactions(connection.access_token, cursor)
        for plaid_tx in payload.get("added", []):
            plaid_acct_id = plaid_tx.get("account_id")
            plaid_acct = plaid_accounts.get(plaid_acct_id)
            if not plaid_acct:
                continue
            account = _ensure_plaid_account(
                db,
                user_id=connection.user_id,
                connection=connection,
                plaid_account=plaid_acct,
            )
            ext_id = plaid_tx.get("transaction_id")
            if ext_id:
                exists = (
                    db.query(Transaction)
                    .filter(Transaction.plaid_transaction_id == ext_id)
                    .first()
                )
                if exists:
                    continue

            raw_amount = float(plaid_tx.get("amount", 0))
            amount = _plaid_amount_to_finsight(raw_amount, account.account_type)
            tx_date = date.fromisoformat(str(plaid_tx.get("date"))[:10])
            category = "Uncategorized"
            pfc = plaid_tx.get("personal_finance_category") or {}
            if pfc.get("primary"):
                category = str(pfc["primary"]).replace("_", " ").title()

            tx = Transaction(
                id=str(uuid.uuid4()),
                account_id=account.id,
                transaction_date=tx_date,
                description=plaid_tx.get("name") or plaid_tx.get("merchant_name") or "Transaction",
                amount=amount,
                category=category,
                merchant=plaid_tx.get("merchant_name"),
                plaid_transaction_id=ext_id,
            )
            db.add(tx)
            new_txs.append(tx)
            added_count += 1

        modified_count += len(payload.get("modified", []))
        cursor = payload.get("next_cursor", cursor)
        has_more = payload.get("has_more", False)

    connection.transactions_cursor = cursor
    from datetime import datetime

    connection.last_synced_at = datetime.utcnow()
    db.commit()

    _embed_transactions(new_txs, db)

    synced = connection.last_synced_at.isoformat() if connection.last_synced_at else None
    return {
        "connection_id": connection.id,
        "institution": connection.institution_name,
        "added": added_count,
        "modified_seen": modified_count,
        "last_synced_at": synced,
    }
