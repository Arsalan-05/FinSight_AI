from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph state carried across agent turns."""

    messages: Annotated[list[BaseMessage], add_messages]
    memory_summary: str
    session_id: str
