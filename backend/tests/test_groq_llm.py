"""Tests for Groq LLM response parsing."""

from __future__ import annotations

import json

from agent.llm import (
    _groq_request_too_large,
    _parse_groq_failed_tool_generation,
    _parse_openai_style_message,
    _to_groq_messages,
)


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


def test_parse_groq_failed_tool_generation_xml_markup() -> None:
    failed = '<function=search_web{"query": "credit card vs debit card"}></function>'
    calls = _parse_groq_failed_tool_generation(failed)
    assert len(calls) == 1
    assert calls[0]["name"] == "search_web"
    assert calls[0]["args"]["query"] == "credit card vs debit card"
    assert calls[0]["id"]


def test_parse_groq_failed_tool_generation_empty_on_garbage() -> None:
    assert _parse_groq_failed_tool_generation("not a tool call") == []


def test_groq_request_too_large_detects_tpm_cap() -> None:
    body = {
        "error": {
            "code": "rate_limit_exceeded",
            "message": (
                "Request too large for model `llama-3.1-8b-instant` "
                "on tokens per minute (TPM): Limit 6000, Requested 11745"
            ),
        }
    }
    assert _groq_request_too_large(body) is True
