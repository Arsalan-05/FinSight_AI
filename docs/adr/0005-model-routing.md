# ADR 0005: Model routing 8B / 70B

## Status

Accepted

## Context

8B is cheap/fast but weaker on multi-step date reasoning; 70B costs more.

## Decision

Classifier routes simple aggregation to Groq 8B; multi-step / planning to 70B (or Claude). Thresholds tuned from Phase 1 evals.

## Consequences

- Lower average $ / query
- Need eval gate so routing regressions are caught
