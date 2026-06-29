# FinSight AI — Project Documentation

> **Author:** Arsalan Amir Ali — portfolio project, built and maintained by me.  
> **Status:** ✅ **COMPLETE** — portfolio-ready, fully tested, documented, and published.

---

## Startup Guide (read this first)

I run FinSight locally in four steps. Copy this block when you need a clean start:

```bash
# 1 — Environment
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
# Fill DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY in both files

# 2 — Database (Supabase direct connection — use hotspot if campus Wi-Fi blocks port 5432)
chmod +x infra/supabase/setup-e2e.sh
./infra/supabase/setup-e2e.sh

# 3 — Ollama models (one-time)
ollama pull llama3.2
ollama pull nomic-embed-text

# 4 — Run services (two terminals)
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google → dashboard loads your data.

**Verify everything:**

```bash
cd backend && set -a && source ../.env && set +a && uv run python scripts/check_e2e.py
cd backend && uv run pytest -q
cd frontend && npm run lint && npm run type-check && npm run build
```

Expected: **16/16** e2e checkpoints, **76** tests passing, frontend build clean.

**Campus Wi-Fi note:** If Supabase Postgres is unreachable, keep `docker compose up -d db` running — the backend auto-falls back to local Postgres (`DATABASE_FALLBACK_ENABLED=true` in `.env.example`).

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [Authentication & User Scoping](#6-authentication--user-scoping)
7. [API Reference](#7-api-reference)
8. [RAG Pipeline](#8-rag-pipeline)
9. [Finance Agent & Chat](#9-finance-agent--chat)
10. [Canadian Fintech Features](#10-canadian-fintech-features)
11. [Frontend](#11-frontend)
12. [Environment Variables](#12-environment-variables)
13. [Setup & Running](#13-setup--running)
14. [Supabase (Auth + Hosted Postgres)](#14-supabase-auth--hosted-postgres)
15. [Testing & Quality](#15-testing--quality)
16. [Troubleshooting](#16-troubleshooting)
17. [Demo Script](#17-demo-script)
18. [How I Explain It (Interviews)](#18-how-i-explain-it-interviews)
19. [Out of Scope](#19-out-of-scope)
20. [Development Commands](#20-development-commands)
21. [Project Complete](#21-project-complete)

---

## 1. Overview

### What I built

**FinSight AI** is my personal finance intelligence app. I upload bank transactions (or use seeded demo data), and a finance agent answers questions like *"How much did I spend on dining last month?"* or *"Find my Interac rent payments"* — grounded in real data, not made-up numbers.

Every chat is saved to Postgres. The agent reads my transactions through scoped SQL and RAG tools, so answers stay tied to what is actually in the database.

### Core capabilities

| Capability | Implementation |
|------------|----------------|
| Structured finance data | PostgreSQL — users, accounts, transactions |
| Semantic search (RAG) | pgvector HNSW + Ollama/Voyage embeddings |
| Reasoning agent | LangGraph ReAct loop with tool calls |
| Auth & multi-user | Supabase Google OAuth + per-user data scoping |
| Proactive insights | Subscriptions, runway, TFSA, anomalies, credit tips |
| Canadian banks | RBC, TD, CIBC, Scotiabank, BMO, Simplii, Interac parser |
| External tools (MCP) | BoC FX rates, currency conversion, demo market quotes |

### How I describe it

I built FinSight to ingest my transaction data, embed it in pgvector for semantic search, and run a stateful finance agent that answers spending questions through SQL and retrieval tools — not guessed numbers. FastAPI serves the API; Next.js is the dashboard, search, and chat UI. Supabase handles Google login; Postgres stores everything including saved chat history. I run it locally with Ollama; the same stack can swap to paid APIs via env vars when needed.

---

## 2. Architecture

### System diagram

```mermaid
flowchart TB
    subgraph client [Frontend — Next.js :3000]
        UI[Dashboard · Analytics · Transactions · Search · Chat · Settings]
        AuthUI[Supabase Auth — Google OAuth]
    end

    subgraph api [Backend — FastAPI :8000]
        JWT[JWKS JWT Verification]
        Routes[REST + SSE /chat]
        Scope[Per-user scoping]
        Agent[Finance Agent — ReAct loop]
        RAG[RAG Retriever]
        Tools[Aggregator + Insights + MCP]
    end

    subgraph data [PostgreSQL + pgvector]
        Rel[(users · accounts · transactions)]
        Vec[(transaction_embeddings HNSW)]
        Sessions[(chat_sessions)]
    end

    subgraph llm [LLM Layer]
        Ollama[Ollama — local default]
        Claude[Anthropic Claude — optional]
    end

    AuthUI -->|session cookies| UI
    UI -->|Bearer JWT + REST/SSE| JWT
    JWT --> Routes
    Routes --> Scope
    Scope --> Rel
    Routes --> Agent
    Agent --> RAG
    Agent --> Tools
    RAG --> Vec
    Tools --> Rel
    Agent --> Ollama
    Agent --> Claude
```

### Data flows

**Ingest**
```
CSV upload → POST /transactions/upload → parse (bank auto-detect + Interac)
  → INSERT transactions → embed (best-effort) → INSERT transaction_embeddings
```

**Search**
```
Natural language query → embed query → pgvector cosine search (HNSW)
  → top-k transactions scoped to logged-in user
```

**Chat**
```
POST /chat (SSE) → load ChatSession → LangGraph ReAct loop
  → tools (search, aggregate, insights, MCP) → stream tokens → save session + citations
```

**Auth sync**
```
Google OAuth → Supabase JWT → POST /auth/sync → link users.auth_id
  → provision demo data if new user has no accounts
```

### Design principles

- **Frontend never touches Postgres** — all data via FastAPI
- **Agent never invents dollar amounts** — must call tools first
- **One database** — relational + vectors in same Postgres (no separate vector DB)
- **Config in environment** — 12-factor; works locally, Docker, and cloud
- **Per-user isolation** — when auth is enforced, all queries scoped by `user_id`

---

## 3. Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Backend | Python 3.11+, FastAPI | AI ecosystem, async, OpenAPI, Pydantic DI |
| Package mgr | `uv` | Fast lockfile installs, used in Docker |
| ORM | SQLAlchemy 2.0 | Typed `Mapped` columns, Alembic migrations |
| Database | PostgreSQL 16 + pgvector | ACID + vectors in one store |
| Migrations | Alembic | Versioned schema changes |
| Agent | LangGraph | Explicit ReAct state machine, testable |
| LLM (default) | Ollama `llama3.2` | Free local inference |
| LLM (optional) | Anthropic Claude | Production-quality reasoning |
| Embeddings (default) | Ollama `nomic-embed-text` (768-dim) | Free local embeddings |
| Embeddings (optional) | Voyage `voyage-3` (1024-dim) | Higher retrieval quality |
| Frontend | Next.js 16 App Router | SSR, standalone Docker output |
| Styling | Tailwind CSS v4 | Glass fintech UI, CSS variables |
| Charts | Recharts | Theme-aware analytics |
| Auth | Supabase (ES256 JWKS) | Google OAuth, no custom auth server |
| Containers | Docker Compose | db + api + frontend |
| CI | GitHub Actions | ruff, mypy, pytest, ESLint, tsc |

---

## 4. Project Structure

```
FinSight_AI/
├── DOCUMENTATION.md          ← This file (master docs)
├── README.md                 ← Quick entry point
├── CLAUDE.md                 ← Dev notes for working in this repo
├── .env.example              ← Environment template
├── docker-compose.yml        ← Local stack orchestration
│
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, routers
│   │   ├── config.py         # pydantic-settings
│   │   ├── auth.py           # Supabase JWT + user sync
│   │   ├── scoping.py        # Per-user data filters
│   │   ├── demo_provision.py # Auto-seed for new OAuth users
│   │   └── routers/          # auth, users, accounts, transactions,
│   │                           # search, chat, insights, goals
│   ├── agent/
│   │   ├── graph.py          # LangGraph ReAct graph
│   │   ├── runner.py         # Chat runner + citations
│   │   ├── llm.py            # Ollama / Anthropic client
│   │   ├── memory.py         # Session summarization
│   │   ├── goals.py          # Financial goals in prompt
│   │   └── tools/            # search, aggregate, insights, dates
│   ├── rag/
│   │   ├── embedder.py       # Ollama / Voyage embeddings
│   │   └── retriever.py      # pgvector cosine search
│   ├── db/
│   │   └── models.py         # SQLAlchemy models
│   ├── ingest/
│   │   ├── bank_csv.py       # Canadian bank CSV parsers
│   │   └── interac.py        # Interac e-Transfer normalizer
│   ├── insights/             # recurring, anomalies, TFSA, runway, credit
│   ├── mcp/                  # BoC rates, currency, market stubs
│   ├── alembic/versions/     # 8 migrations
│   ├── scripts/
│   │   ├── seed.py           # Canadian demo data
│   │   └── check_e2e.py      # Full-stack checkpoint script
│   └── tests/                # 76 pytest tests
│
├── frontend/
│   ├── app/                  # Next.js pages (dashboard, chat, etc.)
│   ├── components/           # UI shell, OnboardingBanner
│   ├── hooks/useAuthReady.ts # JWT hydration + profile sync before API calls
│   └── lib/
│       ├── api.ts            # Typed API client
│       └── supabase/         # Browser + server clients, session
│
└── infra/
    └── supabase/
        ├── setup-e2e.sh      # One-command Supabase setup
        ├── 01_extensions.sql
        └── 02_full_schema.sql
```

---

## 5. Database Schema

### Entity relationships

```
User (1) ──► (N) Account (1) ──► (N) Transaction (1) ──► (0..1) TransactionEmbedding
User (1) ──► (N) ChatSession
```

### Tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `users` | App profile | `id`, `email`, `name`, `auth_id` (Supabase UUID), `goals_json` |
| `accounts` | Financial accounts | `user_id` FK, `institution`, `account_type` (checking/savings/credit) |
| `transactions` | Transaction rows | `account_id` FK, `transaction_date`, `amount` (negative=debit), `category`, `merchant` |
| `transaction_embeddings` | RAG vectors | `transaction_id` FK UNIQUE, `content`, `embedding vector(768)` |
| `chat_sessions` | Agent history | `user_id` FK, `title`, `messages_json`, `memory_summary` |
| `alembic_version` | Migration tracking | `version_num` |

### Indexes

- B-tree: `account_id`, `transaction_date`, `category`, `auth_id`, `user_id` on chat_sessions
- HNSW: `transaction_embeddings.embedding` with `vector_cosine_ops` (m=16, ef_construction=64)

### Amount convention

**Negative = expense (debit). Positive = income (credit).** Matches most bank CSV exports.

### Migrations (Alembic head: `i9d0e1f2a3b4`)

1. `603770f84793` — users, accounts, transactions
2. `a1b2c3d4e5f6` — transaction_embeddings + pgvector
3. `b2c3d4e5f6a7` — chat_sessions
4. `c3d4e5f6a7b8` — resize embeddings to 768 (Ollama)
5. `d4e5f6a7b8c9` — auth_id on users
6. `e5f6a7b8c9d0` — user_id on chat_sessions
7. `f6a7b8c9d0e1` — HNSW index (replaces IVFFlat)
8. `g7b8c9d0e1f2` — goals_json on users
9. `h8c9d0e1f2a3` — title on chat_sessions (history sidebar)
10. `i9d0e1f2a3b4` — pinned on chat_sessions

## 6. Authentication & User Scoping

### Flow

1. User clicks **Continue with Google** on `/login`
2. Supabase OAuth → redirect to `/auth/callback` → session cookies set
3. Middleware protects all routes except `/login` and `/auth/callback`
4. `useAuthReady` hook calls `POST /auth/sync` once the Supabase JWT is ready
5. Backend verifies JWT via **JWKS** (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, ES256)
6. `_sync_user_from_claims` links or creates `users` row with `auth_id = JWT sub`
7. New OAuth users with no accounts get **demo data cloned** automatically (`demo_provision.py`)

### Scoping (`app/scoping.py`)

When a valid JWT is present:

- `accounts_for_user` → only accounts where `user_id = current_user.id`
- `scope_transactions` → only transactions on those accounts
- Empty accounts → zero rows (not all users' data)

When auth is **not** enforced (open dev mode): no filter — all data visible.

### Auth enforcement

```python
auth_enforced = REQUIRE_AUTH or SUPABASE_URL is set
```

Setting `SUPABASE_URL` alone enables auth on protected routes.

### Supabase dashboard requirements

- **Authentication → Providers** → Google enabled
- **URL Configuration** → `http://localhost:3000/auth/callback`
- **Database** → pgvector extension enabled

---

## 7. API Reference

Base URL: `http://localhost:8000` (local)  
Auth: `Authorization: Bearer <supabase_access_token>` on all routes except `/health` and `/health/db` when `REQUIRE_AUTH=true`.

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | `{"status":"ok","environment":"development"}` |
| GET | `/health/db` | No | Reports Supabase vs local Postgres host |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/me` | Current linked app user |
| POST | `/auth/sync` | Sync profile + provision demo data if empty |

### Users

| Method | Path | Description |
|--------|------|-------------|
| POST | `/users/` | Create user |
| GET | `/users/` | List users (open dev only) |
| GET | `/users/{id}` | Get user by ID |

### Accounts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/accounts/` | Create account (scoped to JWT user) |
| GET | `/accounts/` | List current user's accounts |
| GET | `/accounts/{id}` | Get account |
| GET | `/accounts/by-user/{user_id}` | Accounts for user |

### Transactions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/transactions/` | Create single transaction |
| POST | `/transactions/upload` | CSV upload (multipart, auto bank-detect) |
| GET | `/transactions/` | List with filters: `account_id`, `category`, `date_from`, `date_to`, `limit`, `offset` |
| GET | `/transactions/{id}` | Get one |
| DELETE | `/transactions/{id}` | Delete (cascades embedding) |

**CSV required columns:** `date`, `description`, `amount`  
**Optional:** `category`, `merchant`, `notes`

### Search

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/search/` | `{"query":"coffee shops","k":5}` | Semantic transaction search |

### Insights

| Method | Path | Description |
|--------|------|-------------|
| GET | `/insights/` | Proactive cards: subscriptions, rent ratio, runway, TFSA, anomalies, credit |

### Goals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/goals/` | List financial goals |
| POST | `/goals/` | Create goal |
| DELETE | `/goals/{id}` | Delete goal |

### Chat (SSE + history)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/chat/` | `{"message":"...","session_id":"optional"}` | SSE stream; persists session after each turn |
| GET | `/chat/sessions` | — | List saved conversations (pinned first, then newest) |
| GET | `/chat/sessions/{id}` | — | Load messages for history sidebar / resume |
| PATCH | `/chat/sessions/{id}` | `{"title":"...","pinned":true}` | Rename or pin/unpin a conversation |
| DELETE | `/chat/sessions/{id}` | — | Delete a saved conversation (204, removes from DB) |

**SSE events:** `status` (live tool progress), `token`, `done`, `error`

```bash
curl -N -X POST http://localhost:8000/chat/ \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_JWT' \
  -d '{"message":"How much did I spend on dining last month?"}'
```

**Rate limit:** `CHAT_RATE_LIMIT_PER_MINUTE` (default 30, set `0` to disable).

---

## 8. RAG Pipeline

### Indexing (ingest time)

1. `build_content(tx)` formats: `Date | Description | Amount (debit/credit) | Category | Merchant`
2. `embed_texts(contents, input_type="document")` — Ollama (768-d) or Voyage (1024-d)
3. Store in `transaction_embeddings` with CASCADE delete on transaction removal

### Retrieval (query time)

1. Embed user query with `input_type="query"`
2. `ORDER BY embedding.cosine_distance(query_vector) LIMIT k`
3. HNSW index accelerates search at scale

### Why one embedding per transaction?

Personal finance data is row-oriented. Each transaction is a self-contained fact. Paragraph chunking would merge unrelated purchases.

---

## 9. Finance Agent & Chat

I implemented the agent as an explicit ReAct state machine (LangGraph) so every tool call and session turn is testable and persisted in Postgres.

### ReAct loop

```
User message → Agent node (LLM + tool schemas)
  → if tool_calls → Tools node → Agent node
  → else → final answer → stream SSE
```

### Agent tools

| Tool | Purpose |
|------|---------|
| `search_transactions` | RAG semantic search |
| `aggregate_spending` | SQL totals/groups by category, merchant, month |
| `get_financial_insights` | Proactive insight bundle |
| `get_tfsa_status` | TFSA contribution room estimate |
| `get_cash_runway` | Months of runway at current burn |
| `convert_currency` | MCP — FX conversion |
| `get_exchange_rates` | MCP — Bank of Canada live rates |
| `get_market_quote` | MCP — demo stock quotes |

### Session memory

- `chat_sessions.title` — first user message (truncated), shown in history sidebar
- `chat_sessions.messages_json` — full LangChain message history
- `memory_summary` — compressed context across long conversations
- `goals_json` on user — injected into system prompt

### LLM providers

| Provider | Config | Models |
|----------|--------|--------|
| Ollama (default) | `LLM_PROVIDER=ollama` | `llama3.2`, `nomic-embed-text` |
| Anthropic | `LLM_PROVIDER=anthropic` | `claude-sonnet-4-6` |

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

---

## 10. Canadian Fintech Features

### Bank CSV auto-detect (`backend/ingest/bank_csv.py`)

Supported: **RBC, TD, CIBC, Scotiabank, BMO, EQ Bank, Tangerine, Simplii**, plus generic fallback.

### Interac e-Transfer (`backend/ingest/interac.py`)

Parses `INTERAC E-TRANSFER SENT/RECEIVED` descriptions → extracts counterparty, normalizes category.

### Demo persona (`scripts/seed.py` + `canadian_demo.py`)

- York U student — co-op pay, OSAP, GTA rent
- Accounts: RBC Student Chequing + Simplii Cash Back Visa
- ~100 transactions Jan–Jun 2026

### Insights engine (`backend/insights/`)

| Module | Insight |
|--------|---------|
| `recurring.py` | Subscription detection |
| `runway.py` | Cash runway months |
| `tfsa.py` | TFSA contribution room |
| `anomalies.py` | Unusual spending spikes |
| `credit_optimizer.py` | Credit utilization tips |
| `reconciliation.py` | Multi-account net flow |

### BoC FX (`backend/mcp/boc_rates.py`)

Live USD/CAD, EUR/CAD, GBP/CAD from Bank of Canada API.

---

## 11. Frontend

### Routes

| Route | Features |
|-------|----------|
| `/` | Dashboard — KPIs, insight cards, spend chart, recent transactions |
| `/analytics` | Period selector, charts, top merchants, CSV export |
| `/transactions` | CRUD table, filters, bulk delete, CSV upload |
| `/accounts` | Account management |
| `/search` | Semantic search with example queries |
| `/chat` | SSE streaming chat with citations, live status, history sidebar (pin/rename/delete) |
| `/settings` | Health, DB status, goals, export |
| `/login` | Google OAuth + email magic link |

### Key implementation details

- **`lib/api.ts`** — typed client, waits for Supabase JWT before protected calls
- **`hooks/useAuthReady.ts`** — waits for Supabase JWT, runs `/auth/sync`, then allows data fetching
- **Premium UI** — glass surfaces, mesh gradients, dark fintech theme
- **OnboardingBanner** — guides new users to upload CSV or create accounts

### Environment (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## 12. Environment Variables

### Root `.env` (backend + docker-compose)

```env
# ── LLM (free local default) ──────────────────────────────────
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

# ── Paid providers (optional) ─────────────────────────────────
# ANTHROPIC_API_KEY=sk-ant-...
# VOYAGE_API_KEY=pa-...

# ── Supabase Auth ─────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
REQUIRE_AUTH=true

# ── Database ──────────────────────────────────────────────────
# Option A: Supabase hosted Postgres (production path)
USE_SUPABASE_DB=true
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres

# Option B: Local Docker Postgres
# USE_SUPABASE_DB=false
# DATABASE_URL=postgresql://finsight:finsight@localhost:5432/finsight

# Auto-fallback when Supabase is unreachable (campus Wi-Fi):
DATABASE_FALLBACK_URL=postgresql://finsight:finsight@localhost:5432/finsight
DATABASE_FALLBACK_ENABLED=true

PGVECTOR_COLLECTION=transaction_embeddings
ENVIRONMENT=development
NEXT_PUBLIC_API_URL=http://localhost:8000

# ── Optional ──────────────────────────────────────────────────
# FINSIGHT_API_KEY=secret          # Requires X-API-Key header
# CHAT_RATE_LIMIT_PER_MINUTE=30    # 0 = disabled
# SUPABASE_SERVICE_ROLE_KEY=...    # Backend only, not used by routes yet
```

### Notes

- **JWKS auth:** New Supabase projects use ES256 — no `SUPABASE_JWT_SECRET` needed
- **URL-encoded passwords:** If password contains `@`, encode as `%40` in `DATABASE_URL`
- **Alembic:** Percent signs in passwords must be doubled (`%%`) in alembic env — handled in `alembic/env.py`
- **Never commit `.env`** — gitignored

---

## 13. Setup & Running

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for local Postgres option)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js 20+](https://nodejs.org/)
- [Ollama](https://ollama.com) with models:
  ```bash
  ollama pull llama3.2
  ollama pull nomic-embed-text
  ```

### Path A — Local dev with Supabase (recommended)

```bash
cp .env.example .env
# Fill in Supabase keys + DATABASE_URL (see Section 14)

./infra/supabase/setup-e2e.sh   # migrations + seed

cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

### Path B — Local dev with Docker Postgres

```bash
cp .env.example .env
# Set USE_SUPABASE_DB=false, keep local DATABASE_URL

docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head && uv run python scripts/seed.py
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

### Path C — Full Docker stack

```bash
docker compose up --build
```

### Verify everything works

```bash
cd backend && uv run python scripts/check_e2e.py
```

Expected: **16 checkpoints passed** (DB tables, auth, all routes).

---

## 14. Supabase (Auth + Hosted Postgres)

### Architecture

```
Browser → Supabase Auth (login only)
Browser → FastAPI (Bearer JWT + all data CRUD)
FastAPI → Supabase Postgres (users, transactions, embeddings, chat)
```

`users.auth_id` links Supabase `auth.users.id` to app `users.id`.

### One-command setup

```bash
# .env must have DATABASE_URL pointing at Supabase
chmod +x infra/supabase/setup-e2e.sh
./infra/supabase/setup-e2e.sh
```

This runs: connection test → `CREATE EXTENSION vector` → Alembic migrations → `scripts/seed.py`.

### Manual SQL fallback

1. [SQL Editor](https://supabase.com/dashboard/project/_/sql) → run `infra/supabase/02_full_schema.sql`
2. Still set `DATABASE_URL` in `.env` for backend runtime

### Connection string tips

| Type | When to use |
|------|-------------|
| **Direct** `db.PROJECT.supabase.co:5432` | Migrations, local dev on hotspot/home Wi-Fi |
| **Session pooler** `aws-0-REGION.pooler.supabase.com:5432` | App runtime when direct DNS fails |
| **Transaction pooler** port `6543` | Serverless only (not Alembic) |

**Campus Wi-Fi** often blocks port 5432 — use phone hotspot or home network for Supabase Postgres access.

### New OAuth users

On first login, `POST /auth/sync` clones demo data (accounts + transactions + embeddings) if the user has no accounts. Dashboard populates immediately.

---

## 15. Testing & Quality

### Backend

```bash
cd backend
uv run pytest -q                    # 76 tests
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run mypy app/ agent/ db/ rag/ insights/   # type check
uv run python scripts/check_e2e.py  # live integration checkpoint
```

### Frontend

```bash
cd frontend
npm run lint
npm run type-check
npm run build
```

### CI (GitHub Actions)

On every push to `main`: ruff, mypy, pytest, ESLint, `tsc --noEmit`.

### Test coverage highlights

- Health, transactions CRUD, CSV upload
- RAG retriever + embedder
- Agent tool execution + date resolution
- Chat SSE streaming (mocked LLM)
- E2E: upload CSV → chat about it
- Rate limiting, insights, Canadian ingest, demo provisioning

---

## 16. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Could not load your data** | DB unreachable or JWT not ready | Hard refresh; on campus Wi-Fi the backend auto-falls back to local Docker Postgres — run `docker compose up -d db` |
| **API 401 Authentication required** | Missing/expired Bearer token | Sign out and back in; check `SUPABASE_URL` on backend |
| **API 503 auth not configured** | `REQUIRE_AUTH=true` but no `SUPABASE_URL` | Set `SUPABASE_URL` in `.env`, restart backend |
| **Empty dashboard after login** | New user, no data yet | Should auto-provision; if not, run `scripts/seed.py` or upload CSV |
| **DB connection timeout** | Campus Wi-Fi blocks port 5432 | Use hotspot; or use session pooler URL |
| **DNS error on `db.*.supabase.co`** | IPv6/direct connection issue | Use session pooler from Supabase Connect panel |
| **Google login fails** | Provider not enabled | Supabase → Auth → Providers → Google |
| **Redirect error** | Missing callback URL | Add `http://localhost:3000/auth/callback` |
| **Chat no response** | Ollama not running | `ollama serve` + pull models |
| **Embeddings skipped** | Ollama embed model missing | `ollama pull nomic-embed-text` |
| **Alembic % error in password** | ConfigParser interpolation | Fixed in `alembic/env.py` — use URL-encoded password |
| **CORS error** | Wrong origin | API allows localhost + local network IPs |

---

## 17. Demo Script

**My 3-minute walkthrough:**

1. **Login** — Google OAuth → dashboard with insight cards
2. **Dashboard** — subscriptions, rent %, TFSA room, cash runway
3. **Transactions** — upload `samples/rbc_sample.csv` (bank auto-detect)
4. **Search** — *"Interac transfers to landlord"*
5. **Chat** — *"How much TFSA room do I have?"* → answer with transaction citations
6. **Settings** — add goal *"Summer internship relocation $3000"*
7. **Settings → Connections** — Supabase auth + Postgres status

---

## 18. How I Explain It (Interviews)

### Questions I get and how I answer

**Why pgvector instead of Pinecone?**  
I only have thousands of transactions, not millions. I wanted one database to back up and migrate. I can JOIN embeddings to transactions in a single query, and CASCADE delete keeps vectors in sync.

**How do you prevent wrong dollar amounts?**  
The system prompt requires tool calls before answering. The agent has `search_transactions` (semantic retrieval) and `aggregate_spending` (SQL) — it never guesses numbers.

**Why a ReAct graph instead of a simple chain?**  
I needed an explicit loop: the model picks a tool, observes the result, and can iterate. Typed state, testable nodes, and session memory in Postgres made debugging much easier.

**How does auth work?**  
Supabase issues ES256 JWTs. My backend fetches the JWKS public key, verifies the signature, and links `auth_id` to the app user. Every query is scoped by `user_id`.

**Why Ollama for local dev?**  
Zero API cost while I'm iterating. The architecture swaps to Anthropic or Voyage via env vars when I want higher quality.

**What would I add for production?**  
Flinks/Plaid bank sync, Redis rate limiting, Railway deploy with a connection pooler, structured logging, and RLS policies on Supabase.

### Design trade-offs I made

| Decision | Trade-off |
|----------|-----------|
| Client-side analytics | Simple, no extra API — fine for hundreds of rows |
| Demo data clone on login | Fast onboarding — not real bank data until I upload CSV |
| MCP market quotes | Stub data for demo — not a live market feed |
| SQLite in tests | Fast tests — dialect differences handled in the aggregator |
| Single Postgres | Simpler ops — I'd shard only at very large scale |

---

## 19. Out of Scope

Things I intentionally left out (paid contracts, legal review, or ops beyond what I needed for this build):

| Item | Reason |
|------|--------|
| Flinks / Plaid live bank sync | Commercial API + compliance |
| Public production deploy | Project targets private/local demo |
| Mobile native apps | Responsive web is sufficient |
| CRA e-filing | Regulated tax filing |
| Paid Claude/Voyage in CI | Ollama covers free CI path |

---

## 20. Development Commands

```bash
# ── Start everything (Supabase path) ──────────────────────────
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# ── Database ──────────────────────────────────────────────────
docker compose up -d db                              # local Postgres only
cd backend && uv run alembic upgrade head            # run migrations
cd backend && uv run python scripts/seed.py          # seed demo data
./infra/supabase/setup-e2e.sh                        # Supabase full setup

# ── Quality ───────────────────────────────────────────────────
cd backend && uv run pytest -q
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run mypy app/ agent/ db/ rag/ insights/
cd backend && uv run python scripts/check_e2e.py
cd frontend && npm run lint && npm run type-check && npm run build

# ── Agent CLI (debug without frontend) ────────────────────────
cd backend && uv run python -m agent.cli

# ── Docker full stack ─────────────────────────────────────────
docker compose up --build
```

---

## 21. Project Complete

**This project has been completed.**

I built FinSight AI as my personal finance intelligence portfolio system — end to end, from database schema to deployed-quality UI. As of June 2026, every planned feature is implemented, tested, and documented. There are no remaining tasks, stubs, or open build items.

### What ships

| Layer | Delivered |
|-------|-----------|
| **Data** | PostgreSQL + pgvector, Alembic migrations, Canadian bank CSV ingest, per-user scoping |
| **Auth** | Supabase Google OAuth, JWT verification, demo provisioning for new users |
| **RAG** | Transaction embeddings, semantic search, HNSW index |
| **Agent** | ReAct finance agent with SQL + retrieval tools, live status streaming, session memory |
| **Chat** | Saved history in Postgres, pin/rename/delete, citations on answers |
| **Frontend** | Dashboard, analytics, transactions, search, chat, settings — all auth-gated |
| **Reliability** | Local Postgres fallback when Supabase is unreachable, 76 automated tests |
| **Docs** | This file — startup guide, API reference, troubleshooting, interview notes |

### Final verification (June 2026)

```bash
cd backend && uv run pytest -q          # 76 passed
cd backend && uv run ruff check .       # clean
cd frontend && npm run lint && npm run type-check && npm run build   # clean
```

### Repository

Published on GitHub as a private portfolio repository. To run locally, follow the [Startup Guide](#startup-guide-read-this-first) at the top of this document.

**FinSight AI is finished. No further development is planned on this codebase.**

---

## License

Private project — not licensed for redistribution.

---

*Last updated: June 2026 — FinSight AI v1.0.0 (COMPLETE)*
