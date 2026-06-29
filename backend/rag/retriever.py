from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Transaction, TransactionEmbedding
from rag.embedder import embed_texts


def retrieve(
    query: str,
    db: Session,
    k: int = 5,
    *,
    api_key: str = "",
) -> list[Transaction]:
    """Return the top-k transactions most semantically similar to *query*."""
    query_vector = embed_texts([query], input_type="query", api_key=api_key)[0]

    results: list[Transaction] = (
        db.query(Transaction)
        .join(TransactionEmbedding, Transaction.id == TransactionEmbedding.transaction_id)
        .order_by(TransactionEmbedding.embedding.cosine_distance(query_vector))
        .limit(k)
        .all()
    )
    return results
