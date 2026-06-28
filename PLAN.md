# FinSight AI — 8-Week Build Plan

**Goal:** Fully working private finance agent, deployed on Railway, accessible via a URL.
**Timeline:** June 28 – August 23, 2026

---

## Week 1 (Jun 28 – Jul 4) — Project Scaffolding & Dev Environment

**Deliverable:** `docker compose up` starts all services, health checks pass.

- [x] Initialize `backend/` with `uv`, FastAPI, and a `/health` endpoint
- [x] Initialize `frontend/` with Next.js (App Router, TypeScript, Tailwind)
- [x] Set up `infra/` — Docker Compose with services: `api`, `db` (Postgres + pgvector), `frontend`
- [x] `.env.example` with all required vars (`ANTHROPIC_API_KEY`, `DATABASE_URL`, etc.)
- [x] Alembic wired up, initial empty migration runs clean

---

## Week 2 (Jul 5 – Jul 11) — Data Layer (Relational Schema + Ingestion)

**Deliverable:** Upload a CSV of transactions via API, query them back.

- [x] Alembic migrations: `users`, `accounts`, `transactions` tables
- [x] FastAPI CRUD endpoints: ingest transactions (CSV/JSON upload), list/filter
- [x] Pydantic schemas for request/response validation
- [x] Manual test data seeded for development

---

## Week 3 (Jul 12 – Jul 18) — RAG Pipeline

**Deliverable:** Ask "what did I spend on food last month?" and get semantically retrieved transactions back.

- [ ] `transaction_embeddings` table via pgvector
- [ ] Chunking strategy: one embedding per transaction (with rich metadata text)
- [ ] Embedding via Anthropic `claude-sonnet-4-6` or `text-embedding-3-small` fallback
- [ ] Retriever module: top-k cosine similarity search
- [ ] Ingest pipeline: on transaction upload → auto-embed → store in pgvector
- [ ] Unit tests for retriever

---

## Week 4 (Jul 19 – Jul 25) — LangGraph Agent Core

**Deliverable:** CLI-testable agent that answers finance questions with memory.

- [ ] `TypedDict` state: `messages`, `memory_summary`, `session_id`
- [ ] ReAct graph: tool call → observe → respond loop
- [ ] Tool nodes: RAG retriever, spending aggregator (SQL aggregates over `transactions`)
- [ ] Claude API integration (`claude-sonnet-4-6`), prompt caching on system prompt + RAG context
- [ ] Session state persisted in DB across turns
- [ ] Tests via pytest + direct graph invocation (no UI yet)

---

## Week 5 (Jul 26 – Aug 1) — FastAPI Chat Endpoint + MCP Tools

**Deliverable:** `POST /chat` streams a response from the agent.

- [ ] `/chat` endpoint: loads session, runs agent graph, streams response (SSE)
- [ ] FastAPI dependency injection for DB session and agent instance
- [ ] MCP tool servers in `backend/mcp/`: currency conversion, market data (stubs acceptable)
- [ ] Agent registered with MCP tools at startup
- [ ] Integration tests: full request → agent → Claude → response

---

## Week 6 (Aug 2 – Aug 8) — Frontend Chat UI

**Deliverable:** Working chat interface in the browser, connected to the real agent.

- [ ] Next.js chat page: message thread, streaming response display
- [ ] Transaction upload UI: drag-and-drop CSV, progress feedback
- [ ] Basic auth (API key header or HTTP Basic) — private use only
- [ ] Error states, loading states, mobile-responsive layout

---

## Week 7 (Aug 9 – Aug 15) — Docker Polish + Railway Deployment

**Deliverable:** One-click deploy to Railway, accessible via a public URL.

- [ ] Production `Dockerfile` for backend and frontend (multi-stage builds, minimal images)
- [ ] `railway.toml` config: services wired, env vars mapped
- [ ] GitHub Actions CI: lint (`ruff`, ESLint), type-check (`mypy`, `tsc`), pytest on every push
- [ ] Managed Postgres on Railway with pgvector extension enabled
- [ ] Environment variable management (Railway dashboard → service env vars)

---

## Week 8 (Aug 16 – Aug 23) — Testing, Polish, Internship-Ready

**Deliverable:** Stable, demo-able product with real transaction data.

- [ ] Full test coverage: unit (retriever, aggregator), integration (chat endpoint), E2E (upload → chat)
- [ ] pgvector HNSW index for fast retrieval at scale
- [ ] Demo dataset: 3–6 months of realistic transactions (synthetic)
- [ ] README with architecture diagram, setup guide, and live URL
- [ ] Rate limiting on `/chat` to prevent runaway Claude API costs
- [ ] Final QA pass: golden-path demo, edge cases, error recovery

---

## Summary

| Week | Dates | Theme | Key Output |
|------|-------|-------|-----------|
| 1 | Jun 28 – Jul 4 | Scaffolding | Repo + Docker boots |
| 2 | Jul 5 – Jul 11 | Data Layer | Transaction ingestion works |
| 3 | Jul 12 – Jul 18 | RAG | Semantic retrieval works |
| 4 | Jul 19 – Jul 25 | Agent | LangGraph answers questions |
| 5 | Jul 26 – Aug 1 | API | `/chat` endpoint streams |
| 6 | Aug 2 – Aug 8 | UI | Chat interface in browser |
| 7 | Aug 9 – Aug 15 | Deploy | Live on Railway |
| 8 | Aug 16 – Aug 23 | Polish | Demo-ready, tested, documented |

---

> Weeks 4 and 5 are the densest. If schedule slips, buffer time goes there first.
