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
    account_ids: list[str] | None = None,
) -> list[Transaction]:
    """Return the top-k transactions most semantically similar to *query*."""
    query_vector = embed_texts([query], input_type="query", api_key=api_key)[0]

    q = db.query(Transaction).join(
        TransactionEmbedding, Transaction.id == TransactionEmbedding.transaction_id
    )
    if account_ids is not None:
        if not account_ids:
            return []
        q = q.filter(Transaction.account_id.in_(account_ids))

    results: list[Transaction] = (
        q.order_by(TransactionEmbedding.embedding.cosine_distance(query_vector)).limit(k).all()
    )
    return results
