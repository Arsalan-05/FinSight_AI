"""Tests for multi-tier Llama (basic) vs Claude (heavy) routing."""

from __future__ import annotations

from agent.routing import resolve_chat_backend, route_chat_tier, route_model


def test_basic_spend_question_routes_llama() -> None:
    assert route_chat_tier("How much did I spend on dining last month?") == "basic"
    assert route_model("How much did I spend on dining last month?") == "8b"


def test_heavy_planning_routes_claude_tier() -> None:
    q = "Should I compare TFSA vs RRSP for my co-op savings plan?"
    assert route_chat_tier(q) == "heavy"
    assert route_model(q) == "70b"


def test_what_if_is_heavy() -> None:
    assert route_chat_tier("What if I move to Waterloo and pay $1400 rent?") == "heavy"


def test_resolve_heavy_prefers_anthropic(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "privacy_mode", False)
    monkeypatch.setattr(settings, "llm_routing_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(settings, "anthropic_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings, "groq_api_key", "g-test")
    provider, model = resolve_chat_backend("heavy")
    assert provider == "anthropic"
    assert "claude" in model


def test_resolve_heavy_falls_back_to_groq_70b(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "privacy_mode", False)
    monkeypatch.setattr(settings, "llm_routing_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "g-test")
    monkeypatch.setattr(settings, "groq_heavy_model", "llama-3.3-70b-versatile")
    provider, model = resolve_chat_backend("heavy")
    assert provider == "groq"
    assert model == "llama-3.3-70b-versatile"


def test_resolve_basic_uses_groq_8b(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "privacy_mode", False)
    monkeypatch.setattr(settings, "llm_routing_enabled", True)
    monkeypatch.setattr(settings, "groq_api_key", "g-test")
    monkeypatch.setattr(settings, "groq_model", "llama-3.1-8b-instant")
    provider, model = resolve_chat_backend("basic")
    assert provider == "groq"
    assert model == "llama-3.1-8b-instant"


def test_privacy_mode_forces_ollama(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "privacy_mode", True)
    monkeypatch.setattr(settings, "ollama_model", "qwen2.5:7b")
    provider, model = resolve_chat_backend("heavy")
    assert provider == "ollama"
    assert model == "qwen2.5:7b"
