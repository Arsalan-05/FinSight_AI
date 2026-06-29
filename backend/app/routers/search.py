from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.config import settings
from app.dependencies import get_db
from app.schemas import TransactionOut
from app.scoping import account_ids_for_user
from db.models import User
from rag.embedder import ollama_embeddings_available
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
    if settings.embedding_provider == "ollama" and not ollama_embeddings_available():
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
