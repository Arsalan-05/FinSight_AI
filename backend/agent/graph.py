from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agent.llm import call_llm
from agent.prompts import tool_status_label
from agent.state import AgentState
from agent.tools import execute_tool

StatusCallback = Callable[[str, str], None]


def build_graph(
    db: Session,
    account_ids: list[str] | None = None,
    *,
    on_status: StatusCallback | None = None,
) -> Any:
    """Compile a ReAct agent graph: call model → tools → model loop."""

    def _emit(phase: str, detail: str = "") -> None:
        if on_status:
            on_status(phase, detail)

    def agent_node(state: AgentState) -> dict[str, list[AIMessage]]:
        _emit("thinking", "Analyzing your question")
        response = call_llm(
            state["messages"],
            state["memory_summary"],
            user_intelligence=state.get("user_intelligence", ""),
        )
        return {"messages": [response]}

    def tools_node(state: AgentState) -> dict[str, list[ToolMessage]]:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"messages": []}

        def run_one(tc_raw: object) -> ToolMessage:
            tc = cast(dict[str, Any], tc_raw)
            name = tc["name"]
            _emit("tool", tool_status_label(name))
            result = execute_tool(name, tc["args"], db=db, account_ids=account_ids)
            return ToolMessage(content=result, tool_call_id=tc["id"], name=name)

        if len(last.tool_calls) == 1:
            tool_messages = [run_one(last.tool_calls[0])]
        else:
            with ThreadPoolExecutor(max_workers=min(4, len(last.tool_calls))) as pool:
                calls = cast(list[dict[str, Any]], last.tool_calls)
                tool_messages = list(pool.map(run_one, calls))

        _emit("composing", "Writing your answer")
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
