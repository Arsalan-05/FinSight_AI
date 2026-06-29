"""Integration tests for POST /chat SSE endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    return events


class TestChatEndpoint:
    @patch("agent.graph.call_llm")
    def test_chat_streams_tokens_and_done(self, mock_llm: MagicMock, client) -> None:
        mock_llm.return_value = AIMessage(content="You spent $94.75 on dining.")

        response = client.post(
            "/chat/",
            json={"message": "How much did I spend on dining?", "session_id": "chat-test-1"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _parse_sse(response.text)
        token_events = [e for e in events if e.get("type") == "token"]
        done_events = [e for e in events if e.get("type") == "done"]

        assert token_events
        assert done_events
        assert done_events[0]["session_id"] == "chat-test-1"
        assert "94.75" in done_events[0]["content"]

    @patch("agent.graph.call_llm")
    def test_chat_generates_session_id_when_missing(self, mock_llm: MagicMock, client) -> None:
        mock_llm.return_value = AIMessage(content="Hello.")

        response = client.post("/chat/", json={"message": "Hi"})
        assert response.status_code == 200
        events = _parse_sse(response.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["session_id"]

    def test_mcp_currency_tool_registered(self) -> None:
        from agent.tools import get_tool_definitions

        names = {t["name"] for t in get_tool_definitions()}
        assert "convert_currency" in names
        assert "get_market_quote" in names

    def test_mcp_currency_stub(self) -> None:
        from mcp.currency import convert_currency

        result = convert_currency(100, "USD", "CAD")
        assert result["converted_amount"] > 0
        assert result["from_currency"] == "USD"


class TestApiKeyMiddleware:
    def test_rejects_missing_key(self) -> None:
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from app.middleware.api_key import ApiKeyMiddleware

        async def homepage(_request: object) -> PlainTextResponse:
            return PlainTextResponse("ok")

        mini = Starlette(routes=[Route("/", homepage)])
        mini.add_middleware(ApiKeyMiddleware, api_key="secret")
        tc = TestClient(mini)

        assert tc.get("/").status_code == 401
        assert tc.get("/", headers={"X-API-Key": "wrong"}).status_code == 401
        assert tc.get("/", headers={"X-API-Key": "secret"}).status_code == 200

    def test_public_paths_skip_auth(self) -> None:
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from app.middleware.api_key import ApiKeyMiddleware

        async def health(_request: object) -> PlainTextResponse:
            return PlainTextResponse("ok")

        mini = Starlette(routes=[Route("/health", health)])
        mini.add_middleware(ApiKeyMiddleware, api_key="secret")
        tc = TestClient(mini)

        assert tc.get("/health").status_code == 200
