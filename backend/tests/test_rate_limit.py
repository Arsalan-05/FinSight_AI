"""Tests for /chat rate limiting."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.middleware.chat_rate_limit import chat_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    chat_rate_limiter.reset()
    yield
    chat_rate_limiter.reset()


class TestChatRateLimit:
    @patch("agent.graph.call_llm")
    def test_allows_requests_under_limit(self, mock_llm: MagicMock, client, monkeypatch) -> None:
        mock_llm.return_value = AIMessage(content="OK")
        monkeypatch.setattr("app.config.settings.chat_rate_limit_per_minute", 5)

        for _ in range(3):
            r = client.post("/chat/", json={"message": "Hi"})
            assert r.status_code == 200

    @patch("agent.graph.call_llm")
    def test_blocks_requests_over_limit(self, mock_llm: MagicMock, client, monkeypatch) -> None:
        mock_llm.return_value = AIMessage(content="OK")
        monkeypatch.setattr("app.config.settings.chat_rate_limit_per_minute", 2)

        assert client.post("/chat/", json={"message": "one"}).status_code == 200
        assert client.post("/chat/", json={"message": "two"}).status_code == 200
        blocked = client.post("/chat/", json={"message": "three"})
        assert blocked.status_code == 429

    @patch("agent.graph.call_llm")
    def test_disabled_when_limit_zero(self, mock_llm: MagicMock, client, monkeypatch) -> None:
        mock_llm.return_value = AIMessage(content="OK")
        monkeypatch.setattr("app.config.settings.chat_rate_limit_per_minute", 0)

        for _ in range(5):
            assert client.post("/chat/", json={"message": "Hi"}).status_code == 200
