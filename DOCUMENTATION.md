# FinSight AI — Documentation

Version 2.0.0 · complete. This is the reference for how FinSight works, how to run
it, and where the details live. The README has the short version.

## 1. Product

FinSight is a personal-finance assistant for Canadians, built around one rule: the
language model never produces a number on its own. Deterministic Python computes
every amount, the model decides which tools to call and explains the result, and a
guardrail checks each dollar figure in the reply against the tool output before the
user sees it.

| Page | What it does |
|------|--------------|
| Overview (`/`) | Month totals, top categories, 30-day trend, weekly brief with "Ask advisor" shortcuts |
| Chat (`/chat`) | Streaming advisor; several chats can run at once; source chips open the evidence drawer |
| Transactions / Accounts | CSV import, recategorize, rules, account management |
| Search | Natural-language transaction search ("Uber last month over $20") |
| Analytics / Subscriptions | Category trends, recurring charges |
| Leaks | FX markups, duplicates, fees, subscription creep; draft letters |
| Planner / Forecast | TFSA / RRSP / FHSA order, OSAP, student tax, what-if, Monte Carlo bands |
| Notifications | Budget, spend-spike, runway and anomaly alerts |
| Evals | Scores of the eval gate for the deployed build |
| Settings | Alert toggles, learned advisor profile, export, delete account |

## 2. Architecture

| Layer | Technology | Notes |
|-------|------------|-------|
| Web | Next.js 16, React 19, Tailwind 4 | `proxy.ts` refreshes the Supabase session; `/backend/*` is rewritten to the API so the browser only talks to one origin |
| API | FastAPI on Python 3.11 | SSE chat, REST for everything else, `redirect_slashes=False` |
| Agent | LangGraph ReAct loop | Tool-round cap of 6, tier routing per turn, evidence ids on every tool result |
| Data | Supabase Postgres + pgvector, SQLAlchemy 2.1, psycopg 3, Alembic | Supavisor pooler; prepared statements disabled for transaction mode |
| Auth | Supabase Auth (Google, email) | ES256 JWKS verification; invite allowlist |
| Embeddings | Voyage `voyage-4-large`, 1024-d | One vector per transaction, computed at ingest |
| Hosting | Railway (two Docker services), GitHub Actions CI | Push to `main` deploys |

Diagrams, the chat data flow and the migration chain: [`docs/architecture.md`](./docs/architecture.md).

### Chat turn

1. The client creates the session id, so the chat appears in the sidebar immediately.
2. `agent/routing.py` sends lookups to Groq `openai/gpt-oss-20b` and planning, coaching and multi-step questions to Claude `claude-sonnet-4-6` ([ADR 0005](./docs/adr/0005-model-routing.md)). A Groq rate limit falls through to Claude.
3. Tools run SQL aggregates, hybrid search, leak and planning engines, and `calculate` for arithmetic.
4. The reply tags amounts as `[[$412.30|ev_3]]`. The guardrail accepts values that appear in tool output, rounded restatements, sums and differences, period conversions, ratios, and table totals of rows shown in the same reply; anything else becomes `[unverified]`.
5. Messages and evidence are saved; memory and the learned profile update in a background thread.
6. If the stream drops, the client polls the session (`reply_pending`) and picks the answer up when it lands.

### Deterministic engines

| Engine | Location |
|--------|----------|
| Spending aggregates, periods, categories | `agent/tools/`, `agent/tools/dates.py`, `agent/tools/categories.py` |
| Money leaks | `leaks/` (FX via Bank of Canada Valet rates, duplicates, fees, subscription creep, letter drafts) |
| Registered accounts, OSAP, student tax, scenarios | `planning/` with rules in `planning/rules/*.yaml` |
| Monte Carlo forecast | `planning/forecast.py` (seedable) |
| Cash runway, TFSA room, recurring charges, anomalies | `insights/` |
| Safe arithmetic | `agent/tools/calculate.py` (AST whitelist, never `eval`) |

## 3. Data model

Core tables: `users`, `accounts`, `transactions`, `transaction_embeddings`,
`chat_sessions` (messages and evidence as JSON), `budgets`, `notifications`,
`bank_connections`, `leak_findings`, `fx_rates`, `audit_log`, `eval_runs`,
`merchant_aliases`. Amounts are `NUMERIC(12,2)` with debits negative. Every query is
scoped to the caller in the app, and `infra/rls/policies.sql` adds row-level security
for direct Supabase access.

## 4. Configuration

Copy `.env.example` to `.env` (API) and `frontend/.env.local.example` to
`frontend/.env.local` (web). Production values live in Railway variables.

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | yes | Supabase session pooler URL (port 5432) |
| `SUPABASE_URL`, `REQUIRE_AUTH=true` | production | JWT verification |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_HEAVY_MODEL` | yes | Basic tier and heavy fallback |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | recommended | Claude for heavy turns |
| `VOYAGE_API_KEY`, `VOYAGE_MODEL` | yes | Embeddings for search |
| `CORS_ORIGINS` | production | Web origin |
| `BETA_ALLOWED_EMAILS` | optional | Invite allowlist; empty means open |
| `CHAT_RATE_LIMIT_PER_MINUTE` | optional | Default 30 |
| `PLAID_*` | optional | Bank linking (sandbox) |
| `SMTP_*` | optional | Digest email |
| `PRIVACY_MODE` | optional | Forces local Ollama; no cloud LLM |
| `NEXT_PUBLIC_API_URL=/backend`, `API_PROXY_TARGET` | web | Same-origin API proxy; set before the Docker build |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SITE_URL` | web | Auth client and redirects |

`GET /capabilities` shows which providers and models the running API has configured,
without exposing keys.

## 5. Running

Local setup is in the [README](./README.md#run-it-locally); day-to-day commands are in
[DEV.md](./DEV.md). To load a realistic dataset into an account:

```bash
cd backend
uv run python scripts/seed_full.py --email you@example.com
```

This creates four accounts, a year of transactions, planted leaks and embeddings, so
every page and advisor question has data behind it.

## 6. Quality and evaluation

- 332 backend tests (pytest), strict mypy on the core packages, Ruff lint and format.
- ESLint (including the React compiler rules), TypeScript strict, production build.
- Eval gate: 165 questions with SQL ground truth and 60 retrieval queries, scored through the production guardrail. It fails CI and the Docker build below its floors. See [`docs/evals.md`](./docs/evals.md).
- `security.yml` runs `pip-audit` and `npm audit` weekly; both are clean at release.

## 7. Operations

| Endpoint | Use |
|----------|-----|
| `GET /health` | Liveness and running version |
| `GET /health/ready` | Railway health check |
| `GET /health/db` | Database host, connectivity, schema status |
| `GET /health/auth` | Supabase JWKS reachability |
| `GET /capabilities` | Configured providers, models, routing |

Deploy and rollback: [`docs/deploy.md`](./docs/deploy.md),
[`infra/railway/DEPLOY.md`](./infra/railway/DEPLOY.md) and
[`infra/RAILWAY-CHECKLIST.md`](./infra/RAILWAY-CHECKLIST.md). Security model and
PIPEDA mapping: [`docs/security.md`](./docs/security.md). Costs:
[`docs/cost.md`](./docs/cost.md). Categorization: [`docs/categorizer.md`](./docs/categorizer.md).
Release smoke test: [`docs/e2e-checklist.md`](./docs/e2e-checklist.md).

## 8. Known limits

- Statement import is CSV. `ingest/pdf` parses statement text and reconciles balances, but binary PDFs are not read.
- Cash runway is estimated from chequing and savings history because the app does not store bank balances.
- The eval gate grades reference answers offline; live model replies are protected by the guardrail at runtime, not scored.
- Plaid runs against the sandbox environment.
- The free Supabase project pauses after a week without traffic; the `keepalive` workflow pings `/health` when `FINSIGHT_HEALTH_URL` is set.

## 9. Decisions

| ADR | Decision |
|-----|----------|
| [0001](./docs/adr/0001-pgvector-vs-pinecone.md) | pgvector in Postgres instead of a separate vector database |
| [0002](./docs/adr/0002-langgraph-vs-loop.md) | LangGraph instead of a hand-rolled agent loop |
| [0003](./docs/adr/0003-one-embedding-per-transaction.md) | One embedding per transaction |
| [0004](./docs/adr/0004-deterministic-engines.md) | Deterministic engines own all money math |
| [0005](./docs/adr/0005-model-routing.md) | Groq for basic turns, Claude for heavy ones |
| [0006](./docs/adr/0006-hybrid-search-rerank.md) | Hybrid keyword + vector search with RRF |
| [0007](./docs/adr/0007-rls-app-scoping.md) | App scoping plus row-level security |
| [0008](./docs/adr/0008-monte-carlo-forecast.md) | Monte Carlo forecast bands |

## License

MIT. Copyright (c) 2026 Arsalan Amir Ali.
