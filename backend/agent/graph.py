from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agent.llm import call_llm
from agent.state import AgentState
from agent.tools import execute_tool


def build_graph(db: Session, account_ids: list[str] | None = None) -> Any:
    """Compile a ReAct agent graph: call model → tools → model loop."""

    def agent_node(state: AgentState) -> dict[str, list[AIMessage]]:
        response = call_llm(state["messages"], state["memory_summary"])
        return {"messages": [response]}

    def tools_node(state: AgentState) -> dict[str, list[ToolMessage]]:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"messages": []}

        tool_messages: list[ToolMessage] = []
        for tc in last.tool_calls:
            result = execute_tool(tc["name"], tc["args"], db=db, account_ids=account_ids)
            tool_messages.append(
                ToolMessage(content=result, tool_call_id=tc["id"], name=tc["name"])
            )
        return {"messages": tool_messages}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    workflow: StateGraph[AgentState, None, AgentState, AgentState] = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
