from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from db.models import Transaction, TransactionEmbedding
from rag.embedder import build_content, embed_texts, embeddings_runtime_available

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 24


def count_indexed_transactions(db: Session, account_ids: list[str]) -> int:
    if not account_ids:
        return 0
    return (
        db.query(TransactionEmbedding)
        .join(Transaction, Transaction.id == TransactionEmbedding.transaction_id)
        .filter(Transaction.account_id.in_(account_ids))
        .count()
    )


def count_user_transactions(db: Session, account_ids: list[str]) -> int:
    if not account_ids:
        return 0
    return db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).count()


def _unindexed_transactions(
    db: Session, account_ids: list[str], *, limit: int
) -> list[Transaction]:
    return (
        db.query(Transaction)
        .outerjoin(
            TransactionEmbedding,
            Transaction.id == TransactionEmbedding.transaction_id,
        )
        .filter(Transaction.account_id.in_(account_ids))
        .filter(TransactionEmbedding.id.is_(None))
        .order_by(Transaction.transaction_date.desc())
        .limit(limit)
        .all()
    )


def index_transaction_batch(
    db: Session,
    transactions: list[Transaction],
) -> int:
    """Embed and store a single batch (no mass delete)."""
    if not transactions:
        return 0
    if not settings.embeddings_configured or not embeddings_runtime_available():
        raise RuntimeError("Embeddings are not configured on this server")

    contents = [build_content(tx) for tx in transactions]
    try:
        vectors = embed_texts(contents, input_type="document")
    except Exception as exc:
        raise RuntimeError(f"Voyage embedding failed: {exc}") from exc

    if len(vectors) != len(transactions):
        raise RuntimeError("Embedding provider returned an unexpected number of vectors")

    try:
        for tx, content, vector in zip(transactions, contents, vectors):
            db.add(
                TransactionEmbedding(
                    transaction_id=tx.id,
                    content=content,
                    embedding=vector,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist embedding batch")
        raise
    return len(transactions)


def index_missing_batch(
    db: Session,
    account_ids: list[str],
    *,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> tuple[int, int, int, int]:
    """Index up to batch_size transactions missing embeddings.

    Returns (indexed_this_call, transaction_count, indexed_count, remaining).
    """
    total = count_user_transactions(db, account_ids)
    if total == 0:
        return 0, 0, 0, 0

    batch = _unindexed_transactions(db, account_ids, limit=batch_size)
    indexed_now = index_transaction_batch(db, batch)
    indexed_total = count_indexed_transactions(db, account_ids)
    remaining = max(total - indexed_total, 0)
    return indexed_now, total, indexed_total, remaining


def reindex_transactions(db: Session, transactions: list[Transaction]) -> int:
    """Rebuild embeddings for explicit transaction list (used in tests / CSV upload)."""
    if not transactions:
        return 0

    tx_ids = [tx.id for tx in transactions]
    (
        db.query(TransactionEmbedding)
        .filter(TransactionEmbedding.transaction_id.in_(tx_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    indexed = 0
    for start in range(0, len(transactions), _DEFAULT_BATCH_SIZE):
        batch = transactions[start : start + _DEFAULT_BATCH_SIZE]
        indexed += index_transaction_batch(db, batch)
    return indexed
