from __future__ import annotations

import json

from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from sqlalchemy.orm import Session

from db.models import ChatSession


def load_session(db: Session, session_id: str) -> ChatSession:
    """Load an existing session or create a new one."""
    session = db.get(ChatSession, session_id)
    if session is None:
        session = ChatSession(id=session_id, messages_json="[]", memory_summary="")
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def load_messages(session: ChatSession) -> list[BaseMessage]:
    raw = json.loads(session.messages_json or "[]")
    return messages_from_dict(raw)


def save_session(
    db: Session,
    session_id: str,
    messages: list[BaseMessage],
    memory_summary: str,
) -> None:
    session = load_session(db, session_id)
    session.messages_json = json.dumps(messages_to_dict(messages))
    session.memory_summary = memory_summary
    db.commit()
