"""Tests for Groq LLM response parsing."""

from __future__ import annotations

import json

from agent.llm import _parse_openai_style_message, _to_groq_messages


def test_parse_openai_style_message_with_tool_calls() -> None:
    msg = _parse_openai_style_message(
        {
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "aggregate_spending",
                        "arguments": '{"group_by": "category", "transaction_type": "debit"}',
                    },
                }
            ],
        }
    )
    assert msg.tool_calls
    assert msg.tool_calls[0]["name"] == "aggregate_spending"
    assert msg.tool_calls[0]["args"]["group_by"] == "category"


def test_parse_openai_style_message_text_only() -> None:
    msg = _parse_openai_style_message({"content": "You spent $42 on dining."})
    assert msg.content == "You spent $42 on dining."
    assert not msg.tool_calls


def test_to_groq_messages_serializes_tool_arguments_as_json_string() -> None:
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    messages = [
        HumanMessage(content="How much did I spend?"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "aggregate_spending",
                    "args": {"group_by": "category", "transaction_type": "debit"},
                }
            ],
        ),
        ToolMessage(content='{"total": 42}', tool_call_id="call_1"),
    ]
    payload = _to_groq_messages(messages)
    assistant = payload[1]
    assert assistant["role"] == "assistant"
    args = assistant["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args, str)
    assert json.loads(args)["group_by"] == "category"
