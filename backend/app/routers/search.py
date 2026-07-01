from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_current_user_optional
from app.config import settings
from app.dependencies import get_db
from app.schemas import TransactionOut
from app.scoping import account_ids_for_user
from db.models import Transaction, User
from rag.embedder import embeddings_runtime_available
from rag.indexing import count_indexed_transactions, index_missing_batch, reindex_transactions
from rag.retriever import retrieve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    k: int = 5


class SearchResponse(BaseModel):
    results: list[TransactionOut]
    query: str
    k: int
    embedding_enabled: bool


class SearchStatusResponse(BaseModel):
    embedding_enabled: bool
    transaction_count: int
    indexed_count: int
    needs_reindex: bool


class ReindexResponse(BaseModel):
    indexed: int
    transaction_count: int
    indexed_count: int
    remaining: int
    complete: bool


@router.get("/status", response_model=SearchStatusResponse)
def search_status(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> SearchStatusResponse:
    """Report whether semantic search is indexed for the current user."""
    enabled = bool(
        settings.embeddings_configured and embeddings_runtime_available()
    )
    account_ids = account_ids_for_user(db, current_user)
    if not account_ids:
        return SearchStatusResponse(
            embedding_enabled=enabled,
            transaction_count=0,
            indexed_count=0,
            needs_reindex=False,
        )
    tx_count = (
        db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).count()
    )
    indexed = count_indexed_transactions(db, account_ids)
    return SearchStatusResponse(
        embedding_enabled=enabled,
        transaction_count=tx_count,
        indexed_count=indexed,
        needs_reindex=enabled and tx_count > 0 and indexed == 0,
    )


@router.post("/reindex", response_model=ReindexResponse)
def reindex_search_index(
    batch_size: int = Query(default=8, ge=1, le=32),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReindexResponse:
    """Index the next batch of transactions missing embeddings (call until complete)."""
    account_ids = account_ids_for_user(db, current_user)
    if not account_ids:
        return ReindexResponse(
            indexed=0,
            transaction_count=0,
            indexed_count=0,
            remaining=0,
            complete=True,
        )
    try:
        indexed, total, indexed_total, remaining = index_missing_batch(
            db, account_ids, batch_size=batch_size
        )
        return ReindexResponse(
            indexed=indexed,
            transaction_count=total,
            indexed_count=indexed_total,
            remaining=remaining,
            complete=remaining == 0,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Search reindex failed")
        raise HTTPException(
            status_code=502,
            detail="Search indexing failed. Try again in a moment.",
        ) from exc


@router.post("/", response_model=SearchResponse)
def semantic_search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> SearchResponse:
    """Semantic search over transactions using the RAG retriever."""
    if not settings.embeddings_configured:
        return SearchResponse(
            results=[],
            query=payload.query,
            k=payload.k,
            embedding_enabled=False,
        )
    if not embeddings_runtime_available():
        return SearchResponse(
            results=[],
            query=payload.query,
            k=payload.k,
            embedding_enabled=False,
        )
    account_ids = account_ids_for_user(db, current_user)
    try:
        txs = retrieve(payload.query, db, k=payload.k, account_ids=account_ids)
        return SearchResponse(
            results=txs,  # type: ignore[arg-type]
            query=payload.query,
            k=payload.k,
            embedding_enabled=True,
        )
    except Exception:
        logger.exception("Semantic search failed")
        return SearchResponse(
            results=[],
            query=payload.query,
            k=payload.k,
            embedding_enabled=True,
        )
