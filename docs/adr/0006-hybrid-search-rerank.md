# ADR 0006: Hybrid search + rerank

## Status

Accepted

## Context

Pure vector search misses exact merchant and amount queries ("Uber", "$54.99"),
while pure keyword search misses paraphrases ("coffee" → Tim Hortons).

## Decision

Run a keyword ranking (`ILIKE` on description and merchant) and a pgvector cosine
ranking side by side, then fuse them with reciprocal rank fusion (k = 60).
Date, amount and account filters parsed from the query apply as SQL `WHERE`
clauses before either ranking. A token-overlap booster reorders the fused top
results; the `Reranker` protocol in `rag/rerank.py` lets a hosted cross-encoder
replace it without touching the retriever.

## Consequences

- Exact merchant lookups and fuzzy questions both land in the top five
- Fusion runs in Python over at most a few dozen ids per ranking, so it adds no measurable latency
- A Postgres `tsvector` index would push keyword ranking into SQL if transaction counts grow large
