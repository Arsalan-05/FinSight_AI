"""Hybrid retrieval: vector search + keyword ILIKE fused with RRF (and optional filters)."""

from __future__ import annotations

import logging
from typing import Any, Sequence

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Transaction, TransactionEmbedding
from rag.cache import cache_user_key, semantic_cache
from rag.embedder import embed_texts
from rag.filters import QueryFilters, parse_query_filters
from rag.rerank import RankedItem, rerank

logger = logging.getLogger(__name__)

RRF_K = 60


def rrf_fuse(
    ranked_id_lists: Sequence[Sequence[str]],
    *,
    k: int = RRF_K,
    limit: int | None = None,
) -> list[str]:
    """Reciprocal Rank Fusion over multiple ranked id lists.

    score(d) = Σ 1 / (k + rank_i(d)) across lists where d appears.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_id_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
    if limit is not None:
        return ordered[:limit]
    return ordered


def _has_tsvector_column(db: Session) -> bool:
    """Return True if transactions expose a Postgres tsvector search column."""
    try:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql":
            return False
        mapper = sa_inspect(Transaction)
        return any(col.key in {"search_vector", "tsv", "fts"} for col in mapper.columns)
    except Exception:
        return False


def _apply_filters(q: Any, filters: QueryFilters) -> Any:
    if filters.date_from is not None:
        q = q.filter(Transaction.transaction_date >= filters.date_from)
    if filters.date_to is not None:
        q = q.filter(Transaction.transaction_date <= filters.date_to)
    if filters.amount_exact is not None:
        # Match absolute amount (debits stored negative)
        exact = abs(filters.amount_exact)
        q = q.filter(
            or_(
                Transaction.amount == exact,
                Transaction.amount == -exact,
            )
        )
    else:
        if filters.amount_min is not None:
            # "over $50" → abs(amount) >= 50
            q = q.filter(
                or_(
                    Transaction.amount >= filters.amount_min,
                    Transaction.amount <= -filters.amount_min,
                )
            )
        if filters.amount_max is not None:
            q = q.filter(Transaction.amount >= -filters.amount_max)
            q = q.filter(Transaction.amount <= filters.amount_max)
    return q


def _keyword_search(
    db: Session,
    query: str,
    *,
    account_ids: list[str] | None,
    filters: QueryFilters,
    limit: int,
) -> list[str]:
    """ILIKE keyword search on description/merchant; returns ranked transaction ids."""
    tokens = [t for t in query.split() if len(t) > 1][:6]
    if not tokens:
        return []

    q = db.query(Transaction)
    if account_ids is not None:
        if not account_ids:
            return []
        q = q.filter(Transaction.account_id.in_(account_ids))
    q = _apply_filters(q, filters)

    clauses = []
    for tok in tokens:
        like = f"%{tok}%"
        clauses.append(Transaction.description.ilike(like))
        clauses.append(Transaction.merchant.ilike(like))
        clauses.append(Transaction.category.ilike(like))
    q = q.filter(or_(*clauses))
    # Prefer more recent when ranking keywords alone
    rows = q.order_by(Transaction.transaction_date.desc()).limit(limit).all()
    return [tx.id for tx in rows]


def _vector_search(
    db: Session,
    query_vector: list[float],
    *,
    account_ids: list[str] | None,
    filters: QueryFilters,
    limit: int,
) -> list[str]:
    q = db.query(Transaction).join(
        TransactionEmbedding, Transaction.id == TransactionEmbedding.transaction_id
    )
    if account_ids is not None:
        if not account_ids:
            return []
        q = q.filter(Transaction.account_id.in_(account_ids))
    q = _apply_filters(q, filters)
    rows = (
        q.order_by(TransactionEmbedding.embedding.cosine_distance(query_vector)).limit(limit).all()
    )
    return [tx.id for tx in rows]


def retrieve(
    query: str,
    db: Session,
    k: int = 5,
    *,
    api_key: str = "",
    account_ids: list[str] | None = None,
    user_id: str | None = None,
    use_cache: bool = True,
    use_rerank: bool = True,
) -> list[Transaction]:
    """Return top-k transactions for *query* via hybrid RRF (+ filters/rerank).

    When a Postgres ``tsvector`` column is absent (current default), fuses
    keyword ILIKE ranking with vector cosine ranking in Python via RRF.
    """
    filters = parse_query_filters(query)
    search_text = filters.cleaned_query or query

    query_vector = embed_texts([search_text], input_type="query", api_key=api_key)[0]

    cache_key = cache_user_key(user_id, account_ids)
    if use_cache:
        cached = semantic_cache.get(cache_key, query_vector, query_text=search_text)
        if cached is not None and isinstance(cached, list):
            # cached stores transaction ids
            if cached:
                txs = (
                    db.query(Transaction)
                    .filter(Transaction.id.in_(cached))
                    .all()
                )
                by_id = {tx.id: tx for tx in txs}
                return [by_id[i] for i in cached if i in by_id][:k]
            return []

    fetch_n = max(k * 4, 20)

    if _has_tsvector_column(db):
        # Future: SQL tsvector + pgvector RRF. Fall through to Python hybrid for now
        # until a search_vector column is migrated.
        logger.debug("tsvector column present but SQL RRF not wired; using Python hybrid")

    vector_ids = _vector_search(
        db, query_vector, account_ids=account_ids, filters=filters, limit=fetch_n
    )
    keyword_ids = _keyword_search(
        db, search_text, account_ids=account_ids, filters=filters, limit=fetch_n
    )
    fused_ids = rrf_fuse([vector_ids, keyword_ids], limit=fetch_n)

    if not fused_ids:
        return []

    txs = db.query(Transaction).filter(Transaction.id.in_(fused_ids)).all()
    by_id = {tx.id: tx for tx in txs}
    ordered = [by_id[i] for i in fused_ids if i in by_id]

    if use_rerank and ordered:
        ranked = [
            RankedItem(id=tx.id, score=1.0 / (i + 1), payload=tx)
            for i, tx in enumerate(ordered)
        ]
        reranked = rerank(search_text, ranked, top_n=k)
        ordered = [item.payload for item in reranked if item.payload is not None]
    else:
        ordered = ordered[:k]

    if use_cache:
        semantic_cache.set(
            cache_key,
            query_vector,
            [tx.id for tx in ordered],
            query_text=search_text,
        )

    return ordered
