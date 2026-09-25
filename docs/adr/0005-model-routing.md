# ADR 0005: Model routing — Llama basic / Claude heavy

## Status

Accepted (updated 2026-09)

## Context

Simple spend lookups should be fast and cheap. Multi-step planning, tax advice,
comparisons, and money-leak discussions need stronger reasoning.

## Decision

`agent/routing.py` classifies each user turn:

| Tier | When | Provider / model |
|------|------|------------------|
| **basic** | Spend totals, filters, short Q&A | Groq `llama-3.1-8b-instant` |
| **heavy** | Planning, TFSA/RRSP/OSAP, what-if, advice, leaks, tax, long multi-question | **Claude** `claude-sonnet-4-6` when `ANTHROPIC_API_KEY` is set; else Groq `llama-3.3-70b-versatile` |

`LLM_ROUTING_ENABLED=true` (default). `PRIVACY_MODE=true` forces Ollama for all tiers.

Chat ReAct (`agent/graph.py`) resolves the tier once per turn and passes
`provider` + `model` into `call_llm`. Memory summaries and profile learning use
the **basic** utility backend (`resolve_utility_backend`).

## Consequences

- Lower average $ / query (most turns stay on free Groq)
- Claude only burns tokens on deep turns
- Need eval gate so routing regressions are caught
- Without `ANTHROPIC_API_KEY`, heavy falls back to Groq 70B automatically
