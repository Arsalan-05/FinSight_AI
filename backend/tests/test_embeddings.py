"""Tests for Voyage embedding configuration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.config import settings


def test_voyage_model_defaults() -> None:
    assert settings.voyage_model == "voyage-4-large"
    assert settings.voyage_output_dimension == 1024
    assert settings.embedding_provider == "voyage"


@patch("rag.embedder.voyageai.Client")
def test_embed_voyage_uses_configured_model(mock_client_cls: MagicMock) -> None:
    from rag.embedder import _embed_voyage

    mock_client = MagicMock()
    mock_client.embed.return_value = MagicMock(embeddings=[[0.1] * 1024])
    mock_client_cls.return_value = mock_client

    result = _embed_voyage(["coffee shop"], "pa-test", "query")
    assert len(result[0]) == 1024
    mock_client.embed.assert_called_once_with(
        ["coffee shop"],
        model="voyage-4-large",
        input_type="query",
        output_dimension=1024,
    )
