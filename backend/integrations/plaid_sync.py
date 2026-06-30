"""Sync Plaid transactions into FinSight accounts."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.category_rules import resolve_category
from app.config import settings
from db.models import Account, BankConnection, Transaction, TransactionEmbedding, User
from integrations.plaid_client import get_accounts, sync_transactions
from integrations.token_crypto import connection_access_token
from rag.embedder import build_content, embed_texts

logger = logging.getLogger(__name__)


def _embed_transactions(txs: list[Transaction], db: Session) -> None:
    if not settings.embeddings_configured or not txs:
        return
    try:
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


def _reembed_transaction(tx: Transaction, db: Session) -> None:
    if not settings.embeddings_configured:
        return
    try:
        if tx.embedding:
            db.delete(tx.embedding)
        content = build_content(tx)
        vector = embed_texts([content], input_type="document")[0]
        db.add(
            TransactionEmbedding(
                transaction_id=tx.id,
                content=content,
                embedding=vector,
            )
        )
    except Exception:
        logger.exception("Plaid sync: re-embed failed for %s", tx.id)


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


def _category_from_plaid(plaid_tx: dict[str, Any]) -> str:
    pfc = plaid_tx.get("personal_finance_category") or {}
    if pfc.get("primary"):
        return str(pfc["primary"]).replace("_", " ").title()
    return "Uncategorized"


def _fields_from_plaid(
    plaid_tx: dict[str, Any], account_type: str
) -> dict[str, Any]:
    raw_amount = float(plaid_tx.get("amount", 0))
    return {
        "transaction_date": date.fromisoformat(str(plaid_tx.get("date"))[:10]),
        "description": plaid_tx.get("name")
        or plaid_tx.get("merchant_name")
        or "Transaction",
        "amount": _plaid_amount_to_finsight(raw_amount, account_type),
        "category": _category_from_plaid(plaid_tx),
        "merchant": plaid_tx.get("merchant_name"),
        "plaid_transaction_id": plaid_tx.get("transaction_id"),
    }


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
    """Pull new/updated/removed transactions for one bank connection."""
    token = connection_access_token(connection)
    accounts_payload = get_accounts(token)
    plaid_accounts = {a["account_id"]: a for a in accounts_payload.get("accounts", [])}

    added_count = 0
    modified_count = 0
    removed_count = 0
    cursor = connection.transactions_cursor or ""
    has_more = True
    new_txs: list[Transaction] = []

    user = db.get(User, connection.user_id)

    def _with_rules(fields: dict[str, object]) -> dict[str, object]:
        if not user:
            return fields
        fields = dict(fields)
        fields["category"] = resolve_category(
            user,
            description=str(fields["description"]),
            merchant=fields.get("merchant"),  # type: ignore[arg-type]
            default=str(fields["category"]),
        )
        return fields

    while has_more:
        payload = sync_transactions(token, cursor)

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

            fields = _with_rules(_fields_from_plaid(plaid_tx, account.account_type))
            tx = Transaction(id=str(uuid.uuid4()), account_id=account.id, **fields)
            db.add(tx)
            new_txs.append(tx)
            added_count += 1

        for plaid_tx in payload.get("modified", []):
            ext_id = plaid_tx.get("transaction_id")
            if not ext_id:
                continue
            existing = (
                db.query(Transaction)
                .filter(Transaction.plaid_transaction_id == ext_id)
                .first()
            )
            if not existing:
                continue
            account = existing.account
            fields = _with_rules(_fields_from_plaid(plaid_tx, account.account_type))
            for key, value in fields.items():
                if key != "plaid_transaction_id":
                    setattr(existing, key, value)
            _reembed_transaction(existing, db)
            modified_count += 1

        for plaid_tx in payload.get("removed", []):
            ext_id = plaid_tx.get("transaction_id")
            if not ext_id:
                continue
            existing = (
                db.query(Transaction)
                .filter(Transaction.plaid_transaction_id == ext_id)
                .first()
            )
            if existing:
                db.delete(existing)
                removed_count += 1

        cursor = payload.get("next_cursor", cursor)
        has_more = payload.get("has_more", False)

    connection.transactions_cursor = cursor
    connection.last_synced_at = datetime.utcnow()
    db.commit()

    _embed_transactions(new_txs, db)

    from notifications.alerts import check_budget_alerts

    if user:
        check_budget_alerts(db, user)

    synced = connection.last_synced_at.isoformat() if connection.last_synced_at else None
    return {
        "connection_id": connection.id,
        "institution": connection.institution_name,
        "added": added_count,
        "modified": modified_count,
        "removed": removed_count,
        "last_synced_at": synced,
    }
