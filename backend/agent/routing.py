"""Multi-tier chat routing: basic (Llama/Groq) vs heavy (Claude)."""

from __future__ import annotations

import re
from typing import Literal

from app.config import settings

ChatTier = Literal["basic", "heavy"]

# Multi-step / planning / comparison / deep advice → heavy tier (Claude)
_HEAVY_PATTERNS = (
    r"\bwhat[\s-]?if\b",
    r"\bplan\b",
    r"\bplanning\b",
    r"\btfsa\b",
    r"\brrsp\b",
    r"\bfhsa\b",
    r"\bosap\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bversus\b",
    r"\bvs\.?\b",
    r"\bscenario\b",
    r"\bforecast\b",
    r"\bproject(?:ion|ed)?\b",
    r"\boptimiz(?:e|ation)\b",
    r"\bmulti[\s-]?step\b",
    r"\bshould i\b",
    r"\btrade[\s-]?off\b",
    r"\badvise\b",
    r"\badvice\b",
    r"\brecommend\b",
    r"\bstrategy\b",
    r"\bexplain why\b",
    r"\bhelp me (think|decide|understand)\b",
    r"\bdiscuss\b",
    r"\banalyze\b",
    r"\banalys[ei]s\b",
)

_HEAVY_RE = re.compile("|".join(_HEAVY_PATTERNS), re.IGNORECASE)

# Long / multi-sentence questions often need deeper reasoning
_MIN_HEAVY_CHARS = 160


def route_model(question: str) -> str:
    """Backward-compatible: ``\"8b\"`` (basic) or ``\"70b\"`` (heavy)."""
    return "70b" if route_chat_tier(question) == "heavy" else "8b"


def route_chat_tier(question: str) -> ChatTier:
    """Classify a user question as ``basic`` (Llama) or ``heavy`` (Claude)."""
    text = (question or "").strip()
    if not text:
        return "basic"
    if _HEAVY_RE.search(text):
        return "heavy"
    if len(text) >= _MIN_HEAVY_CHARS and text.count("?") >= 2:
        return "heavy"
    if len(text) >= _MIN_HEAVY_CHARS * 2:
        return "heavy"
    return "basic"


def resolve_chat_backend(tier: ChatTier) -> tuple[str, str]:
    """Pick ``(provider, model)`` for a tier.

    - basic → Groq Llama (fast/cheap)
    - heavy → Claude when ``ANTHROPIC_API_KEY`` is set; else stronger Groq; else basic Groq
    - privacy_mode → Ollama only
    """
    if settings.privacy_mode:
        return "ollama", settings.ollama_model

    if not settings.llm_routing_enabled:
        # Legacy single-provider mode
        provider = settings.effective_llm_provider
        if provider == "anthropic":
            return "anthropic", settings.anthropic_model
        if provider == "groq":
            return "groq", settings.groq_model
        return "ollama", settings.ollama_model

    if tier == "heavy":
        if settings.anthropic_api_key:
            return "anthropic", settings.anthropic_model
        if settings.groq_api_key:
            return "groq", settings.groq_heavy_model
        return "ollama", settings.ollama_model

    # basic
    if settings.groq_api_key:
        return "groq", settings.groq_model
    if settings.anthropic_api_key:
        # No Groq key — still allow Claude rather than failing
        return "anthropic", settings.anthropic_model
    return "ollama", settings.ollama_model


def tier_status_label(tier: ChatTier, provider: str, model: str) -> str:
    if tier == "heavy":
        if provider == "anthropic":
            return "Deeper discussion (Claude)"
        return f"Deeper discussion ({model})"
    return f"Quick answer ({model})"
