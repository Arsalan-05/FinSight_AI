"""Optional rerank step — identity / simple boost now; Cohere later."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass
class RankedItem:
    """A retrieve candidate with an opaque id and score."""

    id: str
    score: float
    payload: Any = None


class Reranker(Protocol):
    """Interface for Cohere / cross-encoder rerankers."""

    def rerank(self, query: str, items: Sequence[RankedItem], *, top_n: int) -> list[RankedItem]:
        ...


class IdentityReranker:
    """Pass-through reranker (no model call)."""

    def rerank(self, query: str, items: Sequence[RankedItem], *, top_n: int) -> list[RankedItem]:
        _ = query
        return list(items)[:top_n]


class SimpleBoostReranker:
    """Boost items whose payload text overlaps query tokens."""

    def rerank(self, query: str, items: Sequence[RankedItem], *, top_n: int) -> list[RankedItem]:
        tokens = {t.lower() for t in query.split() if len(t) > 2}
        boosted: list[RankedItem] = []
        for item in items:
            text = ""
            if item.payload is not None:
                text = str(
                    getattr(item.payload, "description", None)
                    or getattr(item.payload, "merchant", None)
                    or item.payload
                ).lower()
            overlap = sum(1 for t in tokens if t in text)
            boosted.append(
                RankedItem(
                    id=item.id,
                    score=item.score + 0.05 * overlap,
                    payload=item.payload,
                )
            )
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted[:top_n]


# Default stub used by retriever — swap for CohereReranker later.
DEFAULT_RERANKER: Reranker = SimpleBoostReranker()


def rerank(
    query: str,
    items: Sequence[RankedItem],
    *,
    top_n: int = 5,
    reranker: Reranker | None = None,
) -> list[RankedItem]:
    """Rerank *items* for *query* using *reranker* (default: simple boost)."""
    engine = reranker or DEFAULT_RERANKER
    return engine.rerank(query, items, top_n=top_n)
