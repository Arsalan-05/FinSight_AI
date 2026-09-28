"""Serialize chat_sessions for the API history endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from db.models import ChatSession


def session_to_summary(session: ChatSession) -> dict[str, Any]:
    raw = json.loads(session.messages_json or "[]")
    return {
        "id": session.id,
        "title": session.title or "New conversation",
        "pinned": bool(session.pinned),
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "message_count": len(raw),
    }


def session_to_detail(session: ChatSession) -> dict[str, Any]:
    raw = json.loads(session.messages_json or "[]")
    messages: list[dict[str, str]] = []
    for item in raw:
        data = item.get("data", {})
        role = item.get("type", "")
        content = data.get("content", "")
        if role == "human" and content:
            messages.append({"role": "user", "content": str(content)})
        elif role == "ai" and content and not data.get("tool_calls"):
            messages.append({"role": "assistant", "content": str(content)})
    return {
        "id": session.id,
        "title": session.title or "New conversation",
        "pinned": bool(session.pinned),
        "messages": messages,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "reply_pending": _reply_pending(session, messages),
    }


# Heavy-tier agent turns finish well inside this; older unanswered turns failed.
_REPLY_PENDING_WINDOW = timedelta(minutes=3)


def _reply_pending(session: ChatSession, messages: list[dict[str, str]]) -> bool:
    """True while the agent is plausibly still writing the reply to the last user turn."""
    if not messages or messages[-1]["role"] != "user" or not session.updated_at:
        return False
    updated = session.updated_at
    if updated.tzinfo is not None:
        updated = updated.astimezone(timezone.utc).replace(tzinfo=None)
    return datetime.utcnow() - updated < _REPLY_PENDING_WINDOW
