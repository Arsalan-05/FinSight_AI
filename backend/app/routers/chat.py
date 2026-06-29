from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agent.runner import AgentResult, run_agent
from app.auth import get_current_user, get_current_user_optional
from app.chat_history import session_to_detail, session_to_summary
from app.dependencies import get_db
from app.middleware.chat_rate_limit import enforce_chat_rate_limit
from app.schemas import ChatRequest
from db.models import ChatSession, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_reply(
    message: str,
    session_id: str,
    db: Session,
    user_id: str | None,
) -> AsyncIterator[str]:
    try:
        result: AgentResult = await asyncio.to_thread(
            run_agent,
            message,
            session_id,
            db,
            user_id=user_id,
        )
        for word in result.reply.split():
            yield _sse({"type": "token", "content": word + " "})
            await asyncio.sleep(0)
        yield _sse(
            {
                "type": "done",
                "session_id": session_id,
                "content": result.reply,
                "citations": result.citations,
            }
        )
    except PermissionError:
        yield _sse({"type": "error", "message": "You do not have access to this chat session."})
    except Exception:
        logger.exception("Chat agent failed")
        yield _sse({"type": "error", "message": "Agent failed to generate a response."})


@router.post("/")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    _rate_limit: None = Depends(enforce_chat_rate_limit),
) -> StreamingResponse:
    """Run the finance agent and stream the reply as Server-Sent Events."""
    session_id = payload.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    return StreamingResponse(
        _stream_reply(payload.message, session_id, db, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    """List saved chat sessions for the logged-in user."""
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    return [session_to_summary(s) for s in rows]


@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Load a saved chat session with message history."""
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_to_detail(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    db.delete(session)
    db.commit()
