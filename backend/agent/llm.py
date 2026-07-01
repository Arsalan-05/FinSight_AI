from __future__ import annotations

import json
import uuid
from typing import Any

import anthropic
import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agent.prompts import build_system_prompt
from agent.tools import TOOL_DEFINITIONS
from app.config import settings

ANTHROPIC_MODEL = "claude-sonnet-4-6"


def _system_text(memory_summary: str, user_intelligence: str = "") -> str:
    return build_system_prompt(memory_summary, user_intelligence=user_intelligence)


# ── Anthropic ─────────────────────────────────────────────────────────────────


def _to_anthropic_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            out.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                blocks: list[dict[str, Any]] = []
                if msg.content:
                    blocks.append({"type": "text", "text": str(msg.content)})
                for tc in msg.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["args"],
                        }
                    )
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": "assistant", "content": str(msg.content)})
        elif isinstance(msg, ToolMessage):
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": str(msg.content),
                        }
                    ],
                }
            )
    return out


def _call_anthropic(
    messages: list[BaseMessage],
    memory_summary: str,
    api_key: str,
    *,
    user_intelligence: str = "",
) -> AIMessage:
    client = anthropic.Anthropic(api_key=api_key)
    system = [
        {
            "type": "text",
            "text": _system_text(memory_summary, user_intelligence),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=system,  # type: ignore[arg-type]
        tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
        messages=_to_anthropic_messages(messages),  # type: ignore[arg-type]
    )

    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                {
                    "id": block.id,
                    "name": block.name,
                    "args": (
                        block.input if isinstance(block.input, dict) else json.loads(block.input)
                    ),
                }
            )
    content = "\n".join(text_parts) if text_parts else ""
    if tool_calls:
        return AIMessage(content=content, tool_calls=tool_calls)
    return AIMessage(content=content)


# ── Ollama (free, local) ──────────────────────────────────────────────────────


def _ollama_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_DEFINITIONS
    ]


def _to_ollama_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            out.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage):
            entry: dict[str, Any] = {"role": "assistant", "content": str(msg.content or "")}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            # Ollama requires arguments as an object, not a JSON string.
                            "arguments": tc["args"] if isinstance(tc["args"], dict) else {},
                        },
                    }
                    for tc in msg.tool_calls
                ]
            out.append(entry)
        elif isinstance(msg, ToolMessage):
            out.append(
                {
                    "role": "tool",
                    "content": str(msg.content),
                    "tool_call_id": msg.tool_call_id,
                }
            )
    return out


def _ollama_chat_options() -> dict[str, object]:
    return {
        "temperature": 0.2,
        "num_predict": settings.ollama_num_predict,
    }


def _call_ollama(
    messages: list[BaseMessage],
    memory_summary: str,
    *,
    user_intelligence: str = "",
) -> AIMessage:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": _system_text(memory_summary, user_intelligence)}
        ]
        + _to_ollama_messages(messages),
        "tools": _ollama_tools(),
        "stream": False,
        "options": _ollama_chat_options(),
        "keep_alive": settings.ollama_keep_alive,
    }
    with httpx.Client(timeout=180.0) as client:
        response = client.post(url, json=payload)
        if response.is_error:
            detail = response.text
            raise RuntimeError(f"Ollama error {response.status_code}: {detail}") from None
        data = response.json()

    msg = data.get("message", {})
    content = msg.get("content", "") or ""
    tool_calls: list[dict[str, Any]] = []
    for tc in msg.get("tool_calls", []):
        fn = tc.get("function", {})
        raw_args = fn.get("arguments", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        tool_calls.append(
            {
                "id": tc.get("id") or str(uuid.uuid4()),
                "name": fn.get("name", ""),
                "args": args if isinstance(args, dict) else {},
            }
        )
    if tool_calls:
        return AIMessage(content=content, tool_calls=tool_calls)
    return AIMessage(content=content)


def _summarize_anthropic(messages: list[BaseMessage], current_summary: str, api_key: str) -> str:
    recent = _recent_exchange(messages)
    if not recent:
        return current_summary
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _memory_prompt(current_summary, recent)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    first = response.content[0]
    if first.type == "text":
        return first.text.strip()
    return current_summary


def _summarize_ollama(messages: list[BaseMessage], current_summary: str) -> str:
    recent = _recent_exchange(messages)
    if not recent:
        return current_summary
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    prompt = _memory_prompt(current_summary, recent)
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            json={
                "model": settings.ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 400},
                "keep_alive": settings.ollama_keep_alive,
            },
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", current_summary)
        return str(content).strip()


def _recent_exchange(messages: list[BaseMessage]) -> list[str]:
    recent: list[str] = []
    for msg in messages[-6:]:
        if isinstance(msg, HumanMessage):
            recent.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            recent.append(f"Assistant: {msg.content}")
    return recent


def _memory_prompt(current_summary: str, recent: list[str]) -> str:
    return (
        "Update this conversation memory summary with key facts from the recent exchange. "
        "Keep it under 200 words. Preserve important financial details "
        "(amounts, categories, dates).\n\n"
        f"Current summary:\n{current_summary or '(empty)'}\n\n"
        f"Recent exchange:\n" + "\n".join(recent)
    )


# ── Public API ────────────────────────────────────────────────────────────────


def llm_runtime_available() -> bool:
    """True when the configured provider can answer chat requests."""
    if settings.effective_llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    return ollama_llm_available()


def chat_unavailable_message() -> str:
    if settings.effective_llm_provider == "anthropic":
        return (
            "Advisor is unavailable — add ANTHROPIC_API_KEY on Render "
            "(Settings → Environment) and redeploy."
        )
    return (
        "Advisor needs Ollama running locally, or set ANTHROPIC_API_KEY for cloud chat."
    )


def call_llm(
    messages: list[BaseMessage],
    memory_summary: str,
    api_key: str = "",
    *,
    user_intelligence: str = "",
) -> AIMessage:
    """Call the configured LLM provider (Ollama by default)."""
    if settings.effective_llm_provider == "anthropic":
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return _call_anthropic(
            messages, memory_summary, key, user_intelligence=user_intelligence
        )
    return _call_ollama(messages, memory_summary, user_intelligence=user_intelligence)


def summarize_memory(
    messages: list[BaseMessage],
    current_summary: str,
    api_key: str = "",
) -> str:
    """Update the rolling memory summary after a conversation turn."""
    if len(messages) < 2:
        return current_summary
    if settings.effective_llm_provider == "anthropic":
        key = api_key or settings.anthropic_api_key
        if not key:
            return current_summary
        return _summarize_anthropic(messages, current_summary, key)
    return _summarize_ollama(messages, current_summary)


def ollama_llm_available() -> bool:
    """Return True when Ollama is running and the chat model is pulled."""
    if settings.effective_llm_provider != "ollama":
        return True
    try:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        with httpx.Client(timeout=3.0) as client:
            response = client.get(url)
            response.raise_for_status()
            models = [m.get("name", "") for m in response.json().get("models", [])]
        prefix = settings.ollama_model.split(":")[0]
        return any(m.startswith(prefix) for m in models)
    except Exception:
        return False


# Backward-compatible alias for tests
call_claude = call_llm
