"""Tests for Groq LLM response parsing."""

from __future__ import annotations

from agent.llm import _parse_openai_style_message


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
