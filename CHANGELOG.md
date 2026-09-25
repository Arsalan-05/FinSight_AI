# Changelog

All notable changes to FinSight AI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Evaluation harness (`backend/evals/`) with golden set, retrieval set, and CI smoke gate
- Trust layer: evidence tags, numeric guardrail, deterministic `calculate` tool
- Money-leak engine: FX markup, duplicates, fee scanner, subscription creep, findings API
- Canadian planning engine: TFSA/RRSP/FHSA optimizer, OSAP planner, Monte Carlo forecast
- Hybrid search (tsvector + pgvector RRF), structured filters, semantic cache
- Security: RLS policies, PII redaction, audit log, threat model
- Docs split into `/docs` with ADRs, metrics.json single source of truth

### Changed
- MIT license clarified (redistribution permitted per MIT terms)
- Embedding docs corrected to Voyage `vector(1024)`
- Ollama documented as optional offline fallback only

## [1.5.1] - 2026-07-01

### Added
- Finance-only advisor scope, background/concurrent chat, unified alert toggles
- Follow-up context and reliable learned profile updates
- Railway production + Supabase + Groq + Voyage stack

## [1.5.0] - 2026-06-30

### Added
- Canadian bank CSV ingest, Plaid sync, budgets, spending insights
- LangGraph ReAct agent with SQL + RAG tools
- pgvector semantic search (Voyage embeddings)

[Unreleased]: https://github.com/Arsalan-05/FinSight_AI/compare/v1.5.1...HEAD
[1.5.1]: https://github.com/Arsalan-05/FinSight_AI/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Arsalan-05/FinSight_AI/releases/tag/v1.5.0
