# FinSight AI — 8-Week Build Plan

**Goal:** Fully working private finance agent, deployed on Railway, accessible via a URL.
**Timeline:** June 28 – August 23, 2026

---

## Week 1 (Jun 28 – Jul 4) — Project Scaffolding & Dev Environment ✅ DONE

**Deliverable:** `docker compose up` starts all services, health checks pass.

- [x] Initialize `backend/` with `uv`, FastAPI, and a `/health` endpoint
- [x] Initialize `frontend/` with Next.js (App Router, TypeScript, Tailwind)
- [x] Set up `infra/` — Docker Compose with services: `api`, `db` (Postgres + pgvector), `frontend`
- [x] `.env.example` with all required vars (`ANTHROPIC_API_KEY`, `DATABASE_URL`, etc.)
- [x] Alembic wired up, initial empty migration runs clean

**Shipped:**
- FastAPI app with `/health`, pydantic-settings config, CORS middleware
- Next.js 16 (App Router, TypeScript, Tailwind v4) — build, lint, type-check all pass
- Docker Compose: `db` (pgvector/pg16 with healthcheck), `api` (waits for db healthy), `frontend`
- Multi-stage Dockerfiles for backend and frontend (standalone Next.js output)
- Alembic reads `DATABASE_URL` from env; `env.py` imports `Base.metadata` for autogenerate
- `npm run type-check` script added; ruff + mypy clean; 1 pytest passing

---

## Week 2 (Jul 5 – Jul 11) — Data Layer (Relational Schema + Ingestion) ✅ DONE

**Deliverable:** Upload a CSV of transactions via API, query them back.

- [x] Alembic migrations: `users`, `accounts`, `transactions` tables
- [x] FastAPI CRUD endpoints: ingest transactions (CSV/JSON upload), list/filter
- [x] Pydantic schemas for request/response validation
- [x] Manual test data seeded for development

**Shipped:**
- SQLAlchemy models: `User`, `Account`, `Transaction` with typed `Mapped` columns and relationships
- Alembic migration `603770f84793` creates all tables with indexes on `account_id`, `transaction_date`, `category`
- `get_db()` FastAPI dependency injection for DB sessions
- Pydantic `Create`/`Out` schemas — `account_type` enum validation, `EmailStr`, `field_validator`
- Endpoints: `POST/GET /users/`, `POST/GET /accounts/`, `POST /transactions/` (JSON), `POST /transactions/upload` (CSV multipart), `GET /transactions/` (filters: account, category, date range, pagination), `GET/DELETE /transactions/{id}`
- `scripts/seed.py` — 1 demo user, 2 accounts (checking + Sapphire Reserve credit), 56 transactions across Apr–Jun 2026 (10 categories)
- `tests/conftest.py` uses SQLite `StaticPool` in-memory DB with `get_db` override
- 7 pytest passing, ruff clean, mypy clean

---

## Week 3 (Jul 12 – Jul 18) — RAG Pipeline ✅ DONE

**Deliverable:** Ask "what did I spend on food last month?" and get semantically retrieved transactions back.

- [x] `transaction_embeddings` table via pgvector — `TransactionEmbedding` model added to `db/models.py` (Vector(1024), cascade delete FK, back-relationship on `Transaction`)
- [x] Dependencies wired: `pgvector>=0.3.6`, `anthropic>=0.40.0`, `voyageai>=0.2.3` in `pyproject.toml`; `VOYAGE_API_KEY` in config + `.env.example`
- [x] Alembic migration: create `vector` extension + `transaction_embeddings` table
- [x] Chunking strategy: one embedding per transaction with rich metadata text (`backend/rag/embedder.py`)
- [x] Embedding via Voyage AI `voyage-3` (1024-dim) — `backend/rag/embedder.py`
- [x] Retriever module: top-k cosine similarity search — `backend/rag/retriever.py`
- [x] Ingest pipeline: on transaction upload → auto-embed → store in pgvector (update `transactions.py` router)
- [x] Unit tests for retriever — `tests/test_retriever.py`

**Shipped:**
- Alembic migration `a1b2c3d4e5f6` — `CREATE EXTENSION IF NOT EXISTS vector`, `transaction_embeddings` table, `ix_transaction_embeddings_transaction_id` B-tree index, IVFFlat index (`lists=100`, cosine ops) for approximate similarity search
- `backend/rag/__init__.py` — package marker
- `backend/rag/embedder.py` — `build_content(tx)` formats date/description/amount/category/merchant/notes into a pipe-delimited string; `embed_texts(texts, api_key, input_type)` calls `voyageai.Client.embed(model="voyage-3")` with correct `input_type` ("document" for indexing, "query" for retrieval)
- `backend/rag/retriever.py` — `retrieve(query, db, api_key, k=5)` embeds the query then runs pgvector cosine distance sort via `.cosine_distance()`
- `app/routers/transactions.py` — `_embed_and_store(txs, db)` helper called after commit in both `create_transaction` and `upload_csv`; silently skips if `VOYAGE_API_KEY` is unset or Voyage API call fails (best-effort, never blocks ingestion)
- `tests/test_retriever.py` — 17 unit tests: 12 for `build_content` (all fields, debit/credit labels, merchant/notes presence), 5 for `retrieve` (results ordering, empty results, `input_type="query"` enforced, k limit respected, vector passed to DB)

---

## UI — Full Frontend (Weeks 1–3 Coverage) ✅ DONE

**Deliverable:** Production-quality Next.js UI covering all data-layer and RAG features, with light/dark mode.

**Pages shipped:**
- [x] `/` — Dashboard: net savings KPI, monthly spend/income with `% vs last month` trend, 30-day daily-spend area sparkline, category breakdown bars, recent transactions list
- [x] `/analytics` — Full analytics: period selector (3M/6M/YTD/12M), 4 KPI cards, grouped income-vs-spend bar chart, category donut chart, daily spend line chart, top-10 merchants ranked list, monthly breakdown table, category detail table, CSV export
- [x] `/transactions` — CRUD table: sortable columns, row checkboxes, bulk delete, per-row delete, filter by account/category/date range, pagination, create modal, CSV upload modal (drag-and-drop), export current view as CSV
- [x] `/accounts` — User and account management: create user modal, create account modal, account cards per user
- [x] `/search` — AI semantic search: natural language input, top-K selector (3–20), search history (localStorage, clearable), example query chips, export results as CSV, Voyage AI status warning
- [x] `/settings` — System status: live API health, Voyage AI / Claude status cards, data stats (users/accounts/transactions), export all transactions, environment info, build roadmap
- [x] `/chat` — Placeholder with agent feature roadmap (Week 4+)

**Infrastructure:**
- [x] `recharts` — Bar, Line, Area, Pie charts with dark/light-aware colors
- [x] `next-themes` — Persistent light/dark mode toggle (Sun/Moon button in sidebar footer)
- [x] Global toast notification system (`contexts/ToastContext.tsx`) — success/error/info, auto-dismiss 3.5 s
- [x] `lib/api.ts` — type-safe API client with auto-paginating `getAllTransactions`
- [x] `lib/utils.ts` — `exportToCsv`, `getDateRange`, `getYearToDateRange`, `monthLabel`
- [x] `lib/chart-theme.ts` — reads CSS variables at runtime so chart colors match the active theme
- [x] Light theme via Tailwind v4 CSS variable remapping (`[data-theme="light"]` inverts zinc palette — zero component changes required)
- [x] Sidebar: Analytics + Settings nav items; theme toggle button

---

## Week 4 (Jul 19 – Jul 25) — LangGraph Agent Core ✅ DONE

**Deliverable:** CLI-testable agent that answers finance questions with memory.

- [x] `TypedDict` state: `messages`, `memory_summary`, `session_id`
- [x] ReAct graph: tool call → observe → respond loop
- [x] Tool nodes: RAG retriever, spending aggregator (SQL aggregates over `transactions`)
- [x] Claude API integration (`claude-sonnet-4-6`), prompt caching on system prompt + RAG context
- [x] Session state persisted in DB across turns
- [x] Tests via pytest + direct graph invocation (no UI yet)

**Shipped:**
- `agent/state.py` — `AgentState` TypedDict with `add_messages` reducer
- `agent/graph.py` — ReAct `StateGraph`: `agent` → `tools` → `agent` loop until no tool calls
- `agent/llm.py` — Pluggable LLM: **Ollama** (free default) or Anthropic Claude; `summarize_memory` for rolling context
- `agent/tools/aggregator.py` — SQL aggregates: group by category/merchant/month, date/account/category/type filters
- `agent/tools/dates.py` — `period` resolution (`last_month`, `this_month`, etc.)
- `agent/tools/summarize.py` — plain-English `summary` field on tool results for small models
- `agent/tools/__init__.py` — `search_transactions` (RAG) + `aggregate_spending`; auto-retry on empty/wrong args
- `agent/memory.py` — `ChatSession` load/save with JSON-serialized LangChain messages
- `agent/runner.py` — `run_agent()` one-turn orchestrator (load → invoke → summarize → persist)
- `agent/cli.py` — CLI entry: `uv run python -m agent.cli "your question"`
- `agent/_warn.py` — suppress harmless urllib3/LangGraph import warnings on macOS
- Alembic migration `b2c3d4e5f6a7` — `chat_sessions` table (`messages_json`, `memory_summary`)
- Alembic migration `c3d4e5f6a7b8` — resize embeddings to 768-dim (Ollama `nomic-embed-text`)
- **Ollama integration** — `LLM_PROVIDER=ollama`, `EMBEDDING_PROVIDER=ollama`; no API keys required
- `scripts/seed.py` — auto-embeds transactions after seeding (Ollama)
- `app/config.py` — loads `.env` from repo root or `backend/`; `localhost` DB default for local dev
- `tests/test_aggregator.py` — 9 unit tests for spending aggregator
- `tests/test_agent.py` — 8 tests: tool execution, session persistence, ReAct loop, multi-turn memory
- `tests/test_tool_dates.py` — 4 tests: period resolution, category=`none` sanitization, auto-retry
- Dependencies: `langgraph>=0.6.11`, `langchain-core>=0.3.86`, `httpx`
- 45 pytest passing, ruff + mypy clean

**Local setup (no paid APIs):** Install [Ollama](https://ollama.com) → `ollama pull llama3.2` + `ollama pull nomic-embed-text` → `docker compose up -d db` → migrate + seed → `uv run python -m agent.cli "…"`

---

## Week 5 (Jul 26 – Aug 1) — FastAPI Chat Endpoint + MCP Tools ✅ DONE

**Deliverable:** `POST /chat` streams a response from the agent.

- [x] `/chat` endpoint: loads session, runs agent graph, streams response (SSE)
- [x] FastAPI dependency injection for DB session and agent instance
- [x] MCP tool servers in `backend/mcp/`: currency conversion, market data (stubs acceptable)
- [x] Agent registered with MCP tools at startup
- [x] Integration tests: full request → agent → Claude → response

**Shipped:**
- `app/routers/chat.py` — `POST /chat/` SSE stream (`token` + `done` events)
- `app/dependencies.py` — `get_db()` + `get_agent_runner()` injection
- `app/schemas.py` — `ChatRequest` (`message`, optional `session_id`)
- `mcp/currency.py` — `convert_currency` stub (USD/CAD/EUR/GBP/PKR demo rates)
- `mcp/market.py` — `get_market_quote` stub (AAPL, MSFT, GOOGL, TSLA, SPY)
- `mcp/registry.py` — MCP tool definitions registered at app startup via lifespan
- `agent/tools/__init__.py` — merges MCP tools into agent tool list
- `tests/test_chat.py` — 4 integration tests (SSE stream, session id, MCP registration)
- `tests/test_mcp.py` — 4 unit tests for MCP stubs
- 53 pytest passing

**Try it:**
```bash
curl -N -X POST http://localhost:8000/chat/ \
  -H 'Content-Type: application/json' \
  -d '{"message":"How much did I spend on dining last month?","session_id":"api-test"}'
```

---

## Week 6 (Aug 2 – Aug 8) — Frontend Chat UI ✅ DONE

**Deliverable:** Working chat interface in the browser, connected to the real agent.

- [x] Next.js chat page: message thread, streaming response display
- [x] Transaction upload UI: drag-and-drop CSV, progress feedback *(shipped in parallel UI work — `/transactions`)*
- [x] Basic auth (API key header) — optional `FINSIGHT_API_KEY` + `X-API-Key` header
- [x] Error states, loading states, mobile-responsive layout

**Shipped:**
- `frontend/app/chat/page.tsx` — live chat with SSE streaming, example prompts, new-chat reset
- `frontend/lib/api.ts` — `chatStream()` async generator parsing SSE events
- `frontend/lib/auth.ts` — API key storage (localStorage) + `authHeaders()` on all requests
- `frontend/app/settings/page.tsx` — API key config UI, updated build progress
- `backend/app/middleware/api_key.py` — optional `X-API-Key` gate when `FINSIGHT_API_KEY` is set
- 55 pytest passing

---

## Week 7 (Aug 9 – Aug 15) — Supabase Auth + Premium UI + Private CI ✅ DONE

**Deliverable:** Private, auth-gated app with polished UI — local only (no public deploy).

- [x] Supabase Google OAuth + email magic link login
- [x] ES256 JWT verification via JWKS on backend
- [x] User sync (`auth_id`) + per-user data scoping on accounts/transactions
- [x] Premium design system (glass, mesh, AppShell, PageHeader)
- [x] UI polish: light/dark readability, sidebar overlap fixes, consistent page layout
- [x] GitHub Actions CI (ruff, mypy, pytest, ESLint, tsc)
- [x] **No Railway** — private local/Docker use only

---

## Week 8 (Aug 16 – Aug 23) — Testing, Polish, Internship-Ready

**Deliverable:** Stable, demo-able product with real transaction data.

- [ ] Full test coverage: unit (retriever, aggregator), integration (chat endpoint), E2E (upload → chat)
- [ ] pgvector HNSW index for fast retrieval at scale
- [ ] Demo dataset: 3–6 months of realistic transactions (synthetic)
- [ ] README with architecture diagram and local setup guide (no live URL)
- [ ] Rate limiting on `/chat` to prevent runaway Claude API costs
- [ ] Final QA pass: golden-path demo, edge cases, error recovery

---

## Summary

| Week | Dates | Theme | Key Output | Status |
|------|-------|-------|-----------|--------|
| 1 | Jun 28 – Jul 4 | Scaffolding | Repo + Docker boots | ✅ Done |
| 2 | Jul 5 – Jul 11 | Data Layer | Transaction ingestion works | ✅ Done |
| 3 | Jul 12 – Jul 18 | RAG | Semantic retrieval works | ✅ Done |
| — | (parallel) | UI | Full frontend + light/dark theme | ✅ Done |
| 4 | Jul 19 – Jul 25 | Agent | LangGraph answers questions | ✅ Done |
| 5 | Jul 26 – Aug 1 | API | `/chat` endpoint streams | ✅ Done |
| 6 | Aug 2 – Aug 8 | UI | Wire chat UI to real agent | ✅ Done |
| 7 | Aug 9 – Aug 15 | Auth + UI | Supabase login, premium UI, CI | ✅ Done |
| 8 | Aug 16 – Aug 23 | Polish | Demo-ready, tested, documented | ⬜ Pending |

---

> Weeks 4 and 5 are the densest. If schedule slips, buffer time goes there first.
