# ADR 0001: pgvector vs Pinecone

## Status

Accepted

## Context

Need semantic search over personal transactions with strong data residency and low cost.

## Decision

Use Postgres + pgvector (HNSW) on Supabase. One embedding row per transaction.

## Consequences

- No third-party vector DB bill or sync lag
- Same RLS/scoping as relational data
- Dimension tied to embedding provider (1024 Voyage / 768 Ollama fallback)
