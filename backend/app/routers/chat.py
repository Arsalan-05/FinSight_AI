from __future__ import annotations

import asyncio
import json
import logging
import queue
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import case
from sqlalchemy.orm import Session

from agent.llm import chat_unavailable_message, llm_runtime_available
from agent.memory import load_messages, load_session, save_session
from agent.runner import AgentResult, run_agent
from agent.scope import finance_scope_refusal
from app.auth import get_current_user, get_current_user_optional
from app.chat_history import session_to_detail, session_to_summary
from app.dependencies import get_db
from app.middleware.chat_rate_limit import enforce_chat_rate_limit
from app.schemas import ChatRequest, ChatSessionUpdate
from db.models import ChatSession, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _chunk_reply(text: str, *, words_per_chunk: int = 3) -> list[str]:
    """Split reply into small chunks for a typewriter effect in the UI."""
    words = text.split()
    if not words:
        return [""]
    chunks: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        part = " ".join(words[i : i + words_per_chunk])
        chunks.append(part + (" " if i + words_per_chunk < len(words) else ""))
    return chunks


async def _stream_scoped_refusal(
    message: str,
    session_id: str,
    db: Session,
    user_id: str | None,
    refusal: str,
) -> AsyncIterator[str]:
    """Skip the agent for off-topic questions — instant reply, no Groq tokens."""
    yield _sse({"type": "session", "session_id": session_id})
    session = load_session(db, session_id, user_id=user_id)
    messages = load_messages(session)
    messages.append(HumanMessage(content=message))
    messages.append(AIMessage(content=refusal))
    save_session(db, session_id, messages, session.memory_summary or "", user_id=user_id)
    for chunk in _chunk_reply(refusal):
        yield _sse({"type": "token", "content": chunk})
        await asyncio.sleep(0.022)
    yield _sse(
        {
            "type": "done",
            "session_id": session_id,
            "content": refusal,
            "citations": [],
        }
    )


async def _stream_reply(
    message: str,
    session_id: str,
    db: Session,
    user_id: str | None,
) -> AsyncIterator[str]:
    status_queue: queue.SimpleQueue[tuple[str, str]] = queue.SimpleQueue()
    result_holder: list[AgentResult] = []
    error_holder: list[Exception] = []

    def on_status(phase: str, detail: str) -> None:
        status_queue.put((phase, detail))

    def run() -> None:
        try:
            if not llm_runtime_available():
                raise RuntimeError(chat_unavailable_message())
            result_holder.append(
                run_agent(
                    message,
                    session_id,
                    db,
                    user_id=user_id,
                    on_status=on_status,
                )
            )
        except PermissionError as exc:
            error_holder.append(exc)
        except Exception as exc:
            logger.exception("Chat agent failed")
            error_holder.append(exc)

    yield _sse({"type": "session", "session_id": session_id})
    yield _sse({"type": "status", "phase": "start", "detail": "Connecting to your data"})

    task = asyncio.create_task(asyncio.to_thread(run))

    while not task.done():
        try:
            phase, detail = status_queue.get_nowait()
            yield _sse({"type": "status", "phase": phase, "detail": detail})
        except queue.Empty:
            await asyncio.sleep(0.05)

    while not status_queue.empty():
        phase, detail = status_queue.get_nowait()
        yield _sse({"type": "status", "phase": phase, "detail": detail})

    if error_holder:
        exc = error_holder[0]
        if isinstance(exc, PermissionError):
            yield _sse({"type": "error", "message": "You do not have access to this chat session."})
        elif isinstance(exc, (RuntimeError, ValueError)):
            yield _sse({"type": "error", "message": str(exc)})
        else:
            yield _sse({"type": "error", "message": "Agent failed to generate a response."})
        return

    result = result_holder[0]
    for chunk in _chunk_reply(result.reply):
        yield _sse({"type": "token", "content": chunk})
        await asyncio.sleep(0.022)

    yield _sse(
        {
            "type": "done",
            "session_id": session_id,
            "content": result.reply,
            "citations": result.citations,
        }
    )


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

    refusal = finance_scope_refusal(payload.message)
    stream = (
        _stream_scoped_refusal(payload.message, session_id, db, user_id, refusal)
        if refusal
        else _stream_reply(payload.message, session_id, db, user_id)
    )

    return StreamingResponse(
        stream,
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
        .order_by(
            case((ChatSession.pinned.is_(True), 0), else_=1),
            ChatSession.updated_at.desc(),
        )
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


@router.patch("/sessions/{session_id}")
def update_chat_session(
    session_id: str,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Rename or pin/unpin a saved chat session."""
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty",
            )
        session.title = title[:255]
    if payload.pinned is not None:
        session.pinned = payload.pinned

    db.commit()
    db.refresh(session)
    return session_to_summary(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id and session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    db.delete(session)
    db.commit()
