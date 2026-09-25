from __future__ import annotations

import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agent.guardrails.evidence import EvidenceStore, attach_evidence_ids_to_tool_result
from agent.llm import call_llm
from agent.prompts import tool_status_label
from agent.state import AgentState
from agent.tools import execute_tool

StatusCallback = Callable[[str, str], None]

# Cap ReAct tool rounds (security.md / Phase 6).
MAX_TOOL_LOOPS = 6

# Light per-tool arg constraints (type / range only — not full JSON Schema).
_TOOL_ARG_RULES: dict[str, dict[str, Any]] = {
    "search_transactions": {
        "query": {"type": str, "required": True, "max_len": 500},
        "k": {"type": int, "min": 1, "max": 50},
    },
    "aggregate_spending": {
        "group_by": {
            "type": str,
            "choices": {"category", "merchant", "month", "none"},
        },
        "transaction_type": {"type": str, "choices": {"all", "debit", "credit"}},
    },
    "calculate": {
        "expression": {"type": str, "required": True, "max_len": 200},
    },
}


def validate_tool_args(name: str, args: dict[str, Any]) -> tuple[bool, str]:
    """Lightweight tool-arg validation. Returns (ok, error_message)."""
    if not isinstance(args, dict):
        return False, "Tool args must be an object"
    rules = _TOOL_ARG_RULES.get(name)
    if not rules:
        return True, ""
    for key, rule in rules.items():
        if rule.get("required") and key not in args:
            return False, f"Missing required arg: {key}"
        if key not in args or args[key] is None:
            continue
        value = args[key]
        expected = rule.get("type")
        if expected is str and not isinstance(value, str):
            return False, f"Arg {key} must be a string"
        if expected is int:
            if isinstance(value, bool) or not isinstance(value, int):
                # JSON numbers sometimes arrive as float
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                    args[key] = value
                else:
                    return False, f"Arg {key} must be an integer"
            if "min" in rule and value < rule["min"]:
                return False, f"Arg {key} below minimum {rule['min']}"
            if "max" in rule and value > rule["max"]:
                return False, f"Arg {key} above maximum {rule['max']}"
        if expected is str and isinstance(value, str):
            if "max_len" in rule and len(value) > rule["max_len"]:
                return False, f"Arg {key} exceeds max length {rule['max_len']}"
            choices = rule.get("choices")
            if choices and value not in choices:
                return False, f"Arg {key} must be one of {sorted(choices)}"
    return True, ""


def _tool_loop_count(messages: list[Any]) -> int:
    return sum(1 for m in messages if isinstance(m, AIMessage) and m.tool_calls)


def build_graph(
    db: Session,
    account_ids: list[str] | None = None,
    *,
    on_status: StatusCallback | None = None,
    evidence_store: EvidenceStore | None = None,
) -> Any:
    """Compile a ReAct agent graph: call model → tools → model loop."""
    store = evidence_store if evidence_store is not None else EvidenceStore()
    store_lock = threading.Lock()

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
            args = tc.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            ok, err = validate_tool_args(name, args)
            _emit("tool", tool_status_label(name))
            if not ok:
                payload: dict[str, Any] = {"error": f"Invalid tool args: {err}"}
            else:
                result = execute_tool(name, args, db=db, account_ids=account_ids)
                try:
                    payload = json.loads(result)
                    if not isinstance(payload, dict):
                        payload = {"value": payload}
                except json.JSONDecodeError:
                    payload = {"raw": result}
            with store_lock:
                eid = store.register(name, args if isinstance(args, dict) else {}, payload)
                payload = attach_evidence_ids_to_tool_result(payload, eid)
            return ToolMessage(
                content=json.dumps(payload),
                tool_call_id=tc["id"],
                name=name,
            )

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
            # Count includes the current AIMessage; stop before a 7th tools round.
            if _tool_loop_count(state["messages"]) > MAX_TOOL_LOOPS:
                return END
            return "tools"
        return END

    workflow: StateGraph[AgentState, None, AgentState, AgentState] = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
