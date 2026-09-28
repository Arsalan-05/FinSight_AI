# ADR 0005: Model routing — Groq basic / Claude heavy

## Status

Accepted (updated 2026-09)

## Context

Simple spend lookups should be fast and cheap. Multi-step planning, tax advice,
comparisons, and money-leak discussions need stronger reasoning.

## Decision

`agent/routing.py` classifies each user turn:

| Tier | When | Provider / model |
|------|------|------------------|
| **basic** | Spend totals, filters, short Q&A | Groq `openai/gpt-oss-20b` |
| **heavy** | Planning, TFSA/RRSP/OSAP, what-if, advice, leaks, tax, long multi-question | **Claude** `claude-sonnet-4-6` when `ANTHROPIC_API_KEY` is set; else Groq `openai/gpt-oss-120b` |

`LLM_ROUTING_ENABLED=true` (default). `PRIVACY_MODE=true` forces Ollama for all tiers.

Chat ReAct (`agent/graph.py`) resolves the tier once per turn and passes
`provider` + `model` into `call_llm`. Memory summaries and profile learning use
the **basic** utility backend (`resolve_utility_backend`).

## Consequences

- Lower average $ / query (most turns stay on free Groq)
- Claude only burns tokens on deep turns
- `tests/test_routing.py` pins which questions land on each tier
- Without `ANTHROPIC_API_KEY`, heavy turns fall back to Groq `openai/gpt-oss-120b` automatically
- A Groq 429 on a basic turn falls through to Claude instead of waiting out the rate limit
