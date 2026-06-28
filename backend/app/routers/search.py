from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.schemas import TransactionOut
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
) -> SearchResponse:
    """Semantic search over transactions using the RAG retriever.

    Returns an empty results list (not an error) when VOYAGE_API_KEY is
    not configured — the UI can show a helpful message in that case.
    """
    if not settings.voyage_api_key:
        return SearchResponse(
            results=[],
            query=payload.query,
            k=payload.k,
            embedding_enabled=False,
        )
    try:
        txs = retrieve(payload.query, db, settings.voyage_api_key, k=payload.k)
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
