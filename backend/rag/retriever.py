from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Transaction, TransactionEmbedding
from rag.embedder import embed_texts


def retrieve(
    query: str,
    db: Session,
    api_key: str,
    k: int = 5,
) -> list[Transaction]:
    """Return the top-k transactions most semantically similar to *query*.

    Embeds the query with input_type="query" then runs a cosine distance
    search via pgvector against the stored 1024-dim transaction embeddings.
    Returns an empty list when the embeddings table has no rows.
    """
    query_vector = embed_texts([query], api_key, input_type="query")[0]

    results: list[Transaction] = (
        db.query(Transaction)
        .join(TransactionEmbedding, Transaction.id == TransactionEmbedding.transaction_id)
        .order_by(TransactionEmbedding.embedding.cosine_distance(query_vector))
        .limit(k)
        .all()
    )
    return results
