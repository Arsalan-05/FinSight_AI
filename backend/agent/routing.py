"""Multi-tier chat routing: basic (Llama/Groq) vs heavy (Claude)."""

from __future__ import annotations

import re
from typing import Literal

from app.config import settings

ChatTier = Literal["basic", "heavy"]

# Multi-step / planning / comparison / deep advice / money recovery → Claude
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
    # Narrow: bare "should I cut back?" stays on fast Llama; invest/compare → Claude
    r"\bshould i (invest|contribute|open|switch|move|compare|prioriti[sz]e)\b",
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
    r"\bleak\b",
    r"\brecover(?:y|ing|ed)?\b",
    r"\bcancel(?:lation)?\b",
    r"\bdispute\b",
    r"\bnegotiat(?:e|ion)\b",
    r"\bbudget(?:ing)?\b",
    r"\bdebt\b",
    r"\binterest rate\b",
    r"\bmortgage\b",
    r"\bretire(?:ment)?\b",
    r"\btax(?:es|able)?\b",
    r"\bpros and cons\b",
    r"\bin depth\b",
    r"\bdeep dive\b",
    r"\bwalk me through\b",
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

    - basic → Groq Llama 8B (fast/cheap)
    - heavy → Claude Sonnet when ``ANTHROPIC_API_KEY`` is set; else Groq 70B; else Ollama
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

    # basic — always prefer fast Llama; Claude only if Groq missing
    if settings.groq_api_key:
        return "groq", settings.groq_model
    if settings.anthropic_api_key:
        return "anthropic", settings.anthropic_model
    return "ollama", settings.ollama_model


def resolve_utility_backend() -> tuple[str, str]:
    """Backend for memory summaries / profile JSON — prefer cheap basic tier."""
    return resolve_chat_backend("basic")


def routing_manifest() -> dict[str, object]:
    """Public description of the live tier map (for ``/capabilities``)."""
    basic_p, basic_m = resolve_chat_backend("basic")
    heavy_p, heavy_m = resolve_chat_backend("heavy")
    return {
        "enabled": settings.llm_routing_enabled and not settings.privacy_mode,
        "privacy_mode": settings.privacy_mode,
        "basic": {
            "provider": basic_p,
            "model": basic_m,
            "label": f"{basic_p}/{basic_m}",
            "role": "Fast spend Q&A, lookups, simple aggregates",
        },
        "heavy": {
            "provider": heavy_p,
            "model": heavy_m,
            "label": f"{heavy_p}/{heavy_m}",
            "role": "Planning, comparisons, advice, leaks, tax, what-if",
        },
        "claude_configured": bool(settings.anthropic_api_key),
        "fallback_without_claude": f"groq/{settings.groq_heavy_model}",
    }


def tier_status_label(tier: ChatTier, provider: str, model: str) -> str:
    """Human + machine-readable status so the UI shows which model is active."""
    short = model.split("/")[-1]
    if provider == "anthropic":
        name = f"Claude · {short}"
    elif provider == "groq":
        name = f"Llama · {short}"
    else:
        name = f"{provider} · {short}"
    if tier == "heavy":
        return f"Deeper discussion · {name}"
    return f"Quick answer · {name}"
