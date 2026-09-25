# ADR 0006: Hybrid search + rerank

## Status

Accepted

## Context

Pure vector search misses exact merchant / amount queries.

## Decision

Postgres `tsvector` + GIN fused with pgvector via reciprocal rank fusion (k=60), then optional Cohere/cross-encoder rerank of top 30 → top 5. Structured date/amount/account filters applied as SQL `WHERE` before search.

## Consequences

- Ablation table in `docs/evals.md` proves each gain
- Extra latency on rerank path
