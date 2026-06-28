from __future__ import annotations

from typing import cast

import voyageai

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


def embed_texts(
    texts: list[str],
    api_key: str,
    input_type: str = "document",
) -> list[list[float]]:
    """Embed texts using Voyage AI voyage-3 (1024-dim).

    input_type should be "document" when indexing transactions and "query"
    when embedding a user question — Voyage AI optimises separately for each.
    """
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]
    result = client.embed(texts, model="voyage-3", input_type=input_type)
    return cast("list[list[float]]", result.embeddings)
