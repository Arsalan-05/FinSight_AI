"""Anthropic message conversion for Claude tool rounds."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.llm import _to_anthropic_messages


def test_consecutive_tool_results_merge_into_one_user_turn() -> None:
    msgs = [
        HumanMessage(content="Plan my TFSA"),
        AIMessage(
            content="",
            tool_calls=[
                {"id": "t1", "name": "get_tfsa_status", "args": {}},
                {"id": "t2", "name": "aggregate_spending", "args": {"months": 3}},
            ],
        ),
        ToolMessage(content='{"room": 7000}', tool_call_id="t1"),
        ToolMessage(content='{"total": 1200}', tool_call_id="t2"),
    ]
    out = _to_anthropic_messages(msgs)
    assert out[0]["role"] == "user"
    assert out[1]["role"] == "assistant"
    assert out[2]["role"] == "user"
    assert isinstance(out[2]["content"], list)
    assert len(out[2]["content"]) == 2
    assert out[2]["content"][0]["type"] == "tool_result"
    assert out[2]["content"][1]["type"] == "tool_result"
