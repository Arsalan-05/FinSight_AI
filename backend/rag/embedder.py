from __future__ import annotations

import time
from typing import cast

import httpx
import voyageai

from app.config import settings
from db.models import Transaction

_VOYAGE_RETRY_ATTEMPTS = 4
_VOYAGE_RETRY_WAIT_SEC = 22  # free tier without billing card: 3 RPM


def voyage_error_message(exc: Exception) -> str:
    """User-facing Voyage error text."""
    msg = str(exc)
    lower = msg.lower()
    if "payment method" in lower or "rate limit" in lower or "rpm" in lower:
        return (
            "Voyage is rate-limited (3 requests/min until you add a billing card). "
            "Add a card at https://dashboard.voyageai.com — free tokens still apply, "
            "limits increase in a few minutes. Then retry rebuild, or wait ~20s between batches."
        )
    return f"Voyage embedding failed: {msg}"


def _voyage_rate_limited(exc: Exception) -> bool:
    lower = str(exc).lower()
    return "rate limit" in lower or "rpm" in lower or "payment method" in lower


def build_content(tx: Transaction) -> str:
    """Format a transaction into a rich text string suitable for embedding."""
    direction = "debit" if float(tx.amount) < 0 else "credit"
    parts = [
        f"Date: {tx.transaction_date}",
        f"Description: {tx.description}",
        f"Amount: ${abs(float(tx.amount)):.2f} ({direction})",
        f"Category: {tx.category}",
    ]
    if tx.merchant:
        parts.append(f"Merchant: {tx.merchant}")
    if tx.notes:
        parts.append(f"Notes: {tx.notes}")
    return " | ".join(parts)


def _embed_ollama(texts: list[str]) -> list[list[float]]:
    """Embed via local Ollama (nomic-embed-text, 768-dim) — offline fallback only."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            json={"model": settings.ollama_embed_model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
    return cast("list[list[float]]", data["embeddings"])


def _embed_voyage(texts: list[str], api_key: str, input_type: str) -> list[list[float]]:
    """Embed via Voyage AI (free tier: voyage-4-large, 200M tokens/account)."""
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]
    last_exc: Exception | None = None
    for attempt in range(_VOYAGE_RETRY_ATTEMPTS):
        try:
            result = client.embed(
                texts,
                model=settings.voyage_model,
                input_type=input_type,
                output_dimension=settings.voyage_output_dimension,
            )
            return cast("list[list[float]]", result.embeddings)
        except Exception as exc:
            last_exc = exc
            if not _voyage_rate_limited(exc) or attempt == _VOYAGE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_VOYAGE_RETRY_WAIT_SEC)
    if last_exc:
        raise last_exc
    raise RuntimeError("Voyage embedding failed")


def embed_texts(
    texts: list[str],
    input_type: str = "document",
    *,
    api_key: str = "",
) -> list[list[float]]:
    """Embed texts using the configured provider (Voyage by default).

    input_type is used by Voyage AI only ("document" vs "query").
    """
    provider = settings.effective_embedding_provider
    if provider == "voyage":
        key = api_key or settings.voyage_api_key
        if not key:
            raise ValueError("VOYAGE_API_KEY is required when EMBEDDING_PROVIDER=voyage")
        return _embed_voyage(texts, key, input_type)
    return _embed_ollama(texts)


def embeddings_runtime_available() -> bool:
    """True when semantic search can embed queries and documents."""
    provider = settings.effective_embedding_provider
    if provider == "voyage":
        return bool(settings.voyage_api_key)
    return ollama_embeddings_available()


def embeddings_unavailable_message() -> str:
    provider = settings.effective_embedding_provider
    if provider == "voyage":
        return (
            "Semantic search needs a free VOYAGE_API_KEY (dash.voyageai.com) "
            "on Mac and Render — 200M free tokens with voyage-4-large."
        )
    return (
        "Semantic search needs Ollama with nomic-embed-text, or set VOYAGE_API_KEY "
        "for cloud embeddings (recommended)."
    )


def ollama_embeddings_available() -> bool:
    """Return True when Ollama is running and the embed model is pulled."""
    if settings.effective_embedding_provider != "ollama":
        return True
    try:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        with httpx.Client(timeout=3.0) as client:
            response = client.get(url)
            response.raise_for_status()
            models = [m.get("name", "") for m in response.json().get("models", [])]
        prefix = settings.ollama_embed_model.split(":")[0]
        return any(m.startswith(prefix) for m in models)
    except Exception:
        return False
