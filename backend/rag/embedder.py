from __future__ import annotations

from typing import cast

import httpx
import voyageai

from app.config import settings
from db.models import Transaction


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
    """Embed via local Ollama (nomic-embed-text, 768-dim) — free, no API key."""
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
    """Embed via Voyage AI voyage-3 (1024-dim) — requires VOYAGE_API_KEY."""
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]
    result = client.embed(texts, model="voyage-3", input_type=input_type)
    return cast("list[list[float]]", result.embeddings)


def embed_texts(
    texts: list[str],
    input_type: str = "document",
    *,
    api_key: str = "",
) -> list[list[float]]:
    """Embed texts using the configured provider (Ollama by default).

    input_type is used by Voyage AI only ("document" vs "query").
    """
    if settings.embedding_provider == "voyage":
        key = api_key or settings.voyage_api_key
        if not key:
            raise ValueError("VOYAGE_API_KEY is required when EMBEDDING_PROVIDER=voyage")
        return _embed_voyage(texts, key, input_type)
    return _embed_ollama(texts)


def ollama_embeddings_available() -> bool:
    """Return True when Ollama is running and the embed model is pulled."""
    if settings.embedding_provider != "ollama":
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
