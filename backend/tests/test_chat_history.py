"""Tests for chat session history API and serializers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from agent.memory import save_session
from app.auth import get_current_user
from app.chat_history import session_to_detail, session_to_summary
from app.main import app
from db.models import ChatSession, User


class TestChatHistorySerializers:
    def test_session_to_summary(self, db_session) -> None:
        session = ChatSession(
            id="s1",
            user_id="u1",
            title="Dining spend",
            messages_json=json.dumps(
                [
                    {"type": "human", "data": {"content": "Hi", "type": "human"}},
                    {"type": "ai", "data": {"content": "Hello", "type": "ai"}},
                ]
            ),
            memory_summary="",
        )
        db_session.add(session)
        db_session.commit()

        summary = session_to_summary(session)
        assert summary["id"] == "s1"
        assert summary["title"] == "Dining spend"
        assert summary["message_count"] == 2

    def test_session_to_detail_skips_tool_calls(self) -> None:
        session = ChatSession(
            id="s2",
            title="",
            messages_json=json.dumps(
                [
                    {"type": "human", "data": {"content": "How much on food?", "type": "human"}},
                    {
                        "type": "ai",
                        "data": {"content": "", "type": "ai", "tool_calls": [{"name": "search"}]},
                    },
                    {"type": "ai", "data": {"content": "You spent $50.", "type": "ai"}},
                ]
            ),
            memory_summary="",
        )
        detail = session_to_detail(session)
        assert detail["title"] == "New conversation"
        assert len(detail["messages"]) == 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["content"] == "You spent $50."


class TestChatSessionRoutes:
    @patch("agent.graph.call_llm")
    def test_list_and_get_sessions(self, mock_llm: MagicMock, client, db_session) -> None:
        mock_llm.return_value = AIMessage(content="You spent $42 on dining.")

        user = User(id="user-hist", email="hist@test.com", name="Hist User")
        db_session.add(user)
        db_session.commit()

        def override_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_user
        try:
            client.post(
                "/chat/",
                json={"message": "Dining total?", "session_id": "hist-session-1"},
            )
            session = db_session.get(ChatSession, "hist-session-1")
            assert session is not None
            session.user_id = user.id
            db_session.commit()

            listed = client.get("/chat/sessions")
            assert listed.status_code == 200
            rows = listed.json()
            assert len(rows) == 1
            assert rows[0]["id"] == "hist-session-1"
            assert "Dining" in rows[0]["title"]

            detail = client.get("/chat/sessions/hist-session-1")
            assert detail.status_code == 200
            body = detail.json()
            assert body["messages"][0]["role"] == "user"
            assert "Dining" in body["messages"][0]["content"]

            deleted = client.delete("/chat/sessions/hist-session-1")
            assert deleted.status_code == 204
            assert deleted.content == b""
            assert client.get("/chat/sessions/hist-session-1").status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_save_session_sets_title_from_first_message(self, db_session) -> None:
        save_session(
            db_session,
            "title-test",
            [HumanMessage(content="What did I spend on groceries?"), AIMessage(content="$120")],
            "",
            user_id="u1",
        )
        session = db_session.get(ChatSession, "title-test")
        assert session is not None
        assert session.title == "What did I spend on groceries?"

    @patch("agent.graph.call_llm")
    def test_patch_pin_and_rename(self, mock_llm: MagicMock, client, db_session) -> None:
        mock_llm.return_value = AIMessage(content="Done.")

        user = User(id="user-patch", email="patch@test.com", name="Patch User")
        db_session.add(user)
        session = ChatSession(id="patch-session", user_id=user.id, title="Old title", pinned=False)
        db_session.add(session)
        db_session.commit()

        def override_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_user
        try:
            renamed = client.patch(
                "/chat/sessions/patch-session",
                json={"title": "Rent planning"},
            )
            assert renamed.status_code == 200
            assert renamed.json()["title"] == "Rent planning"

            pinned = client.patch(
                "/chat/sessions/patch-session",
                json={"pinned": True},
            )
            assert pinned.status_code == 200
            assert pinned.json()["pinned"] is True

            listed = client.get("/chat/sessions").json()
            assert listed[0]["id"] == "patch-session"
            assert listed[0]["pinned"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_delete_orphan_session_without_user_id(self, client, db_session) -> None:
        user = User(id="orphan-user", email="orphan@test.com", name="Orphan")
        db_session.add(user)
        orphan = ChatSession(id="orphan-session", user_id=None, title="Old chat")
        db_session.add(orphan)
        db_session.commit()

        def override_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_user
        try:
            assert client.delete("/chat/sessions/orphan-session").status_code == 204
            assert db_session.get(ChatSession, "orphan-session") is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
