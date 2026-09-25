# ADR 0004: Deterministic engines + LLM explainer

## Status

Accepted

## Context

LLMs invent arithmetic; finance products cannot.

## Decision

All money math (aggregates, leaks, TFSA/RRSP/FHSA, OSAP, Monte Carlo) runs in pure Python. The LLM only selects tools and explains results. A `calculate` tool handles ad-hoc arithmetic via a safe expression evaluator.

## Consequences

- Numeric guardrail can verify every `$` / `%` against tool output
- Pitch line: "never lets the LLM do the math"
