# ADR 0002: LangGraph vs plain tool loop

## Status

Accepted

## Context

Finance Q&A needs multi-step tool use with clear stop conditions.

## Decision

LangGraph ReAct loop with capped iterations (6 in v2.0), Pydantic-validated tool args, graceful fallback.

## Consequences

- Observable graph steps for tracing
- Harder to debug than a for-loop initially; mitigated by Langfuse/OTel
