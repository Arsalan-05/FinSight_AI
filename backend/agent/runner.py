from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session

from agent.graph import build_graph
from agent.llm import summarize_memory
from agent.memory import load_messages, load_session, save_session
from app.config import settings


def _last_ai_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            return str(msg.content)
    return ""


def run_agent(
    user_message: str,
    session_id: str,
    db: Session,
    *,
    update_memory: bool = True,
) -> str:
    """Run one agent turn: load session → invoke graph → persist state → return reply."""
    session = load_session(db, session_id)
    messages = load_messages(session)
    messages.append(HumanMessage(content=user_message))

    graph = build_graph(db)
    result = graph.invoke(
        {
            "messages": messages,
            "memory_summary": session.memory_summary or "",
            "session_id": session_id,
        }
    )

    final_messages: list[BaseMessage] = result["messages"]
    memory_summary: str = result.get("memory_summary", session.memory_summary or "")

    if update_memory and settings.llm_configured:
        memory_summary = summarize_memory(final_messages, memory_summary)

    save_session(db, session_id, final_messages, memory_summary)
    return _last_ai_text(final_messages)
