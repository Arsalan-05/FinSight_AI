from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from agent.goals import goals_summary_for_prompt
from agent.graph import build_graph
from agent.llm import summarize_memory
from agent.memory import load_messages, load_session, save_session
from agent.user_profile import (
    build_data_profile,
    load_agent_profile,
    profile_narrative,
    save_agent_profile,
    update_learned_profile,
)
from app.config import settings
from app.scoping import account_ids_for_user
from db.models import User

StatusCallback = Callable[[str, str], None]


@dataclass
class AgentResult:
    reply: str
    citations: list[dict[str, Any]] = field(default_factory=list)


def _last_ai_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            return str(msg.content)
    return ""


def _extract_citations(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Pull transaction citations from tool results used during the turn."""
    seen: set[str] = set()
    citations: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(str(msg.content))
        except json.JSONDecodeError:
            continue
        if msg.name == "search_transactions":
            for r in data.get("results", []):
                tid = r.get("id")
                if tid and tid not in seen:
                    seen.add(tid)
                    citations.append(
                        {
                            "id": tid,
                            "date": r.get("date"),
                            "description": r.get("description"),
                            "amount": r.get("amount"),
                            "category": r.get("category"),
                            "merchant": r.get("merchant"),
                            "source": "semantic_search",
                        }
                    )
        elif msg.name == "get_financial_insights":
            for item in data.get("subscriptions", {}).get("items", []):
                for tid in item.get("transaction_ids", []):
                    if tid not in seen:
                        seen.add(tid)
                        citations.append(
                            {
                                "id": tid,
                                "description": item.get("merchant"),
                                "amount": -item.get("amount", 0),
                                "category": item.get("category"),
                                "source": "recurring_detection",
                            }
                        )
    return citations[:12]


def _should_update_memory(messages: list[BaseMessage]) -> bool:
    """Summarize on first turn, then every other turn, to balance speed and context."""
    human_turns = sum(1 for m in messages if isinstance(m, HumanMessage))
    return human_turns == 1 or (human_turns > 0 and human_turns % 2 == 0)


def run_agent(
    user_message: str,
    session_id: str,
    db: Session,
    *,
    user_id: str | None = None,
    update_memory: bool = True,
    on_status: StatusCallback | None = None,
) -> AgentResult:
    """Run one agent turn: load → invoke → persist → return reply + citations."""
    if on_status:
        on_status("loading", "Loading your conversation")

    session = load_session(db, session_id, user_id=user_id)
    messages = load_messages(session)
    messages.append(HumanMessage(content=user_message))

    account_ids = None
    goals_text = ""
    user: User | None = None
    data_profile: dict[str, Any] = {}
    learned_profile: dict[str, Any] = {}
    user_intelligence = ""

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            account_ids = account_ids_for_user(db, user)
            goals_text = goals_summary_for_prompt(user)
            data_profile = build_data_profile(db, account_ids=account_ids)
            learned_profile = load_agent_profile(user)
            user_intelligence = profile_narrative(data_profile, learned_profile)

    memory = session.memory_summary or ""
    if goals_text:
        memory = f"{memory}\n\n{goals_text}".strip()

    graph = build_graph(db, account_ids=account_ids, on_status=on_status)
    result = graph.invoke(
        {
            "messages": messages,
            "memory_summary": memory,
            "user_intelligence": user_intelligence,
            "session_id": session_id,
        },
        config={"recursion_limit": 18},
    )

    final_messages: list[BaseMessage] = result["messages"]
    memory_summary: str = result.get("memory_summary", session.memory_summary or "")

    if update_memory and settings.llm_configured and _should_update_memory(final_messages):
        memory_summary = summarize_memory(final_messages, memory_summary)

    if user and settings.llm_configured and _should_update_memory(final_messages):
        updated = update_learned_profile(final_messages, learned_profile, data_profile)
        if updated != learned_profile:
            save_agent_profile(db, user, updated)

    save_session(db, session_id, final_messages, memory_summary, user_id=user_id)
    reply = _last_ai_text(final_messages)
    citations = _extract_citations(final_messages)
    return AgentResult(reply=reply, citations=citations)
