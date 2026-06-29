from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_agent_runner, get_db
from app.schemas import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_reply(
    message: str,
    session_id: str,
    db: Session,
    runner: Callable[..., str],
) -> AsyncIterator[str]:
    try:
        reply = await asyncio.to_thread(runner, message, session_id, db)
        for word in reply.split():
            yield _sse({"type": "token", "content": word + " "})
            await asyncio.sleep(0)
        yield _sse({"type": "done", "session_id": session_id, "content": reply})
    except Exception:
        logger.exception("Chat agent failed")
        yield _sse({"type": "error", "message": "Agent failed to generate a response."})


@router.post("/")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    runner: Callable[..., str] = Depends(get_agent_runner),
) -> StreamingResponse:
    """Run the finance agent and stream the reply as Server-Sent Events."""
    session_id = payload.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _stream_reply(payload.message, session_id, db, runner),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
