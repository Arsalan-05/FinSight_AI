"""End-to-end flow: ingest transactions then chat about them."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    return events


def _make_user(client):
    r = client.post("/users/", json={"email": "e2e@example.com", "name": "E2E User"})
    assert r.status_code == 201
    return r.json()


def _make_account(client, user_id: str):
    r = client.post(
        "/accounts/",
        json={
            "user_id": user_id,
            "name": "Checking",
            "institution": "Chase",
            "account_type": "checking",
        },
    )
    assert r.status_code == 201
    return r.json()


class TestUploadToChatE2E:
    @patch("agent.graph.call_llm")
    def test_csv_upload_then_chat(self, mock_llm: MagicMock, client) -> None:
        mock_llm.return_value = AIMessage(content="You spent $21.49 on dining this month.")

        user = _make_user(client)
        account = _make_account(client, user["id"])

        csv_content = (
            "date,description,amount,category,merchant\n"
            "2026-06-01,Starbucks,-5.50,Dining,Starbucks\n"
            "2026-06-02,Chipotle,-15.99,Dining,Chipotle\n"
            "2026-06-03,Salary,4500.00,Income,Acme Corp\n"
        )
        upload = client.post(
            "/transactions/upload",
            params={"account_id": account["id"]},
            files={"file": ("txns.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert upload.status_code == 201
        assert upload.json()["created"] == 3

        listed = client.get("/transactions/", params={"account_id": account["id"]})
        assert listed.status_code == 200
        assert listed.json()["total"] == 3

        chat = client.post(
            "/chat/",
            json={
                "message": "How much did I spend on dining?",
                "session_id": "e2e-upload-chat",
            },
        )
        assert chat.status_code == 200
        events = _parse_sse(chat.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "dining" in done["content"].lower()
        assert done["session_id"] == "e2e-upload-chat"

    @patch("agent.graph.call_llm")
    def test_multi_turn_chat_persists_session(self, mock_llm: MagicMock, client) -> None:
        mock_llm.side_effect = [
            AIMessage(content="Your top category is Dining."),
            AIMessage(content="You had 2 dining transactions."),
        ]

        session_id = "e2e-multi-turn"
        first = client.post(
            "/chat/",
            json={"message": "What is my top spending category?", "session_id": session_id},
        )
        assert first.status_code == 200

        second = client.post(
            "/chat/",
            json={"message": "How many transactions was that?", "session_id": session_id},
        )
        assert second.status_code == 200
        events = _parse_sse(second.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["session_id"] == session_id
