# ADR 0003: One embedding per transaction

## Status

Accepted

## Context

Chunking strategies vary; transactions are already atomic facts.

## Decision

Embed one rich text string per transaction (date, merchant, category, amount, description). Enrich with normalized merchant in v2.0.

## Consequences

- Simple deletes via CASCADE
- Reindex is batched for Voyage rate limits
