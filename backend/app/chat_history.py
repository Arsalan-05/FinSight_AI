"""Serialize chat_sessions for the API history endpoints."""

from __future__ import annotations

import json
from typing import Any

from db.models import ChatSession


def session_to_summary(session: ChatSession) -> dict[str, Any]:
    raw = json.loads(session.messages_json or "[]")
    return {
        "id": session.id,
        "title": session.title or "New conversation",
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
        "messages": messages,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
