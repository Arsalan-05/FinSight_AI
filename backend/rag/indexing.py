from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from db.models import Transaction, TransactionEmbedding
from rag.embedder import build_content, embed_texts, embeddings_runtime_available

logger = logging.getLogger(__name__)

_BATCH_SIZE = 64


def count_indexed_transactions(db: Session, account_ids: list[str]) -> int:
    if not account_ids:
        return 0
    return (
        db.query(TransactionEmbedding)
        .join(Transaction, Transaction.id == TransactionEmbedding.transaction_id)
        .filter(Transaction.account_id.in_(account_ids))
        .count()
    )


def reindex_transactions(db: Session, transactions: list[Transaction]) -> int:
    """Rebuild Voyage/Ollama embeddings for the given transactions."""
    if not transactions:
        return 0
    if not settings.embeddings_configured or not embeddings_runtime_available():
        raise RuntimeError("Embeddings are not configured on this server")

    tx_ids = [tx.id for tx in transactions]
    (
        db.query(TransactionEmbedding)
        .filter(TransactionEmbedding.transaction_id.in_(tx_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    indexed = 0
    for start in range(0, len(transactions), _BATCH_SIZE):
        batch = transactions[start : start + _BATCH_SIZE]
        try:
            contents = [build_content(tx) for tx in batch]
            vectors = embed_texts(contents, input_type="document")
            for tx, content, vector in zip(batch, contents, vectors):
                db.add(
                    TransactionEmbedding(
                        transaction_id=tx.id,
                        content=content,
                        embedding=vector,
                    )
                )
            db.commit()
            indexed += len(batch)
        except Exception:
            db.rollback()
            logger.exception("Embedding batch failed at offset %s", start)
            raise
    return indexed
