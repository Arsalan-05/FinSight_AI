# FinSight AI: resume metrics audit

Audit date: 2026-11-15. Repo state: `main` at `6936ca6` (tag `v2.0.0`), clean working tree.
Scope: read-only. Nothing was edited, committed, pushed or deployed apart from creating this file and `audit/metrics_queries.sql`. No paid LLM or embedding API was called.

**Confidence labels**
- **EXACT**: counted from code or git, or produced by a command run during this audit.
- **ESTIMATE**: a heuristic, or a figure the repo states without measuring it.
- **NEEDS DASHBOARD**: only a live system can answer it.

Secrets: the repo root has an untracked, git-ignored `.env` (`.gitignore:155`). It contains live-looking credentials named `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `VOYAGE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_DB_PASSWORD`, `DATABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. No values were printed or copied. No secrets are tracked in git (`.env.example` only).

---

## 1. Code facts

| Metric | Value | Source | Confidence |
|---|---|---|---|
| Tracked files | 348 | `git ls-files \| wc -l` | EXACT |
| Python lines, all (199 `.py` files) | 23,266 lines (19,689 non-blank) | `git ls-files '*.py' \| xargs cat \| wc -l`; non-blank via `grep -cv '^\s*$'` | EXACT (physical lines incl. comments; no cloc installed) |
| Python lines, backend app code (excl. tests) | 18,170 lines (15,511 non-blank) | same, `backend/*.py ':!backend/tests/*'` | EXACT |
| Python lines, tests | 5,011 lines (4,110 non-blank) | same, `backend/tests/*.py` | EXACT |
| TypeScript/TSX lines (65 files: 45 `.tsx`, 20 `.ts`) | 11,236 lines (10,305 non-blank) | same, `frontend/*.ts frontend/*.tsx` | EXACT |
| CSS / SQL / YAML (workflows+rules) | 1,331 / 222 / 391 lines | `wc -l` by extension | EXACT |
| REST endpoints (unique method+path) | **78** | Decorators in `backend/app/main.py` (4 health routes) + 17 router files in `backend/app/routers/` (`accounts, audit, auth, budgets, capabilities, chat, dashboard, evals_api, goals, insights, integrations, leaks, notifications, planner, search, transactions, users`). 95 raw decorators; duplicates for `""` and `"/"` aliases removed by script | EXACT |
| Router modules mounted | 17 | `backend/app/main.py:80-96` `include_router` | EXACT |
| Frontend pages / route handlers | 16 `page.tsx` + 1 `route.ts` (`auth/callback`) | `git ls-files 'frontend/app/**/page.tsx'` | EXACT |
| Alembic migrations | **17** | `backend/alembic/versions/*.py` | EXACT |
| Database tables (ORM) | **13**: users, accounts, transactions, bank_connections, chat_sessions, transaction_embeddings, budgets, notifications, fx_rates, leak_findings, merchant_aliases, audit_log, eval_runs | `backend/db/models.py` `__tablename__` | EXACT |
| Tables never written by app code | 2 (`audit_log`, `eval_runs`) | `grep -rn 'AuditLog(\|EvalRun('` finds only the class definitions | EXACT |
| Background jobs/workers | 3 in-process: Plaid sync loop (every 4 h), weekly digest loop (daily check), in-memory CSV ingest job queue (daemon threads) | `backend/app/main.py:44-45`, `backend/integrations/plaid_background.py:34,50`, `backend/ingest/jobs.py` | EXACT |
| Parallel tool execution | up to 4 threads per agent step | `backend/agent/graph.py:159` | EXACT |
| Backend automated tests | **335** collected | `pytest --collect-only -q` → `335 tests collected`; 299 `def test_` + parametrized cases | EXACT |
| Backend tests passing locally | **335 / 335** | `pytest -q -p no:cacheprovider` with all secrets blanked: 333 passed; the 2 failures (`TestWebSearch`) came from my own `WEB_SEARCH_ENABLED=false` override, and both pass under default config (`2 passed in 0.05s`). Full suite ran in about 5 s | EXACT |
| Same figure stored in repo | 335 passed, 0 failed | `docs/metrics.json` → `tests.backend` | EXACT (matches) |
| Property-based tests | 1 file uses Hypothesis | `backend/tests/test_propertyish.py` | EXACT |
| Frontend automated tests that run | **0** (`lib/evidence.test.ts` is a placeholder: "skipped until Vitest is added") | `frontend/lib/evidence.test.ts:2`; no test script in `frontend/package.json` | EXACT |
| GitHub Actions workflows | 4: `ci.yml`, `security.yml`, `keepalive.yml`, `pages.yml` | `.github/workflows/` | EXACT |
| CI gates (block merge) | Backend: `ruff check`, `mypy` (strict) on `app/ agent/ db/ rag/ insights/`, `pytest`, eval smoke gate. Frontend: `eslint`, `tsc --noEmit`, `next build` | `.github/workflows/ci.yml` | EXACT |
| Security scans | `pip-audit` + `npm audit` on push/PR and weekly. **Non-blocking** (`continue-on-error: true`) | `.github/workflows/security.yml` | EXACT |
| Other workflows | Weekly production `/health` check that opens an issue on failure; GitHub Pages docs deploy | `keepalive.yml`, `pages.yml` | EXACT |
| Commits | **166** | `git rev-list --count HEAD` | EXACT |
| Contributors | **1** (Arsalan-05, 166 commits) | `git shortlog -sn HEAD` | EXACT |
| First / latest commit | 2026-05-17 / 2026-09-28 | `git log --reverse` / `git log -1` | EXACT |
| Distinct days with commits | 11 | `git log --date=short \| sort -u` | EXACT |
| Releases (tags) | 3: v1.5.0, v1.5.1 (2026-07-01), v2.0.0 (2026-09-28) | `git for-each-ref refs/tags` | EXACT |
| Architecture decision records | 8 | `docs/adr/0001…0008` | EXACT |
| Docker | 2 Dockerfiles (backend `python:3.11-slim` + uv; frontend 2-stage `node:22-alpine`); 2 compose files (`db`, `api`, `frontend`; demo: `db`, `api`) | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose*.yml` | EXACT |
| Eval gate in Docker build | Backend image build runs smoke + full evals and fails on gate | `backend/Dockerfile` `RUN python -m evals.run …` | EXACT |
| Deploy target | Railway, 2 services, Dockerfile builder. API healthcheck `/health/ready`, 120 s timeout, restart on failure (max 5 API / 10 web) | `backend/railway.toml`, `frontend/railway.toml` | EXACT |

## 2. Countable features

| Metric | Value | Source | Confidence |
|---|---|---|---|
| External services integrated | **12**: Groq, Anthropic (Claude), Voyage AI, Supabase (Postgres + Auth), Plaid, Bank of Canada Valet API, Yahoo Finance, Finnhub, Tavily, DuckDuckGo, SMTP email, Ollama (local fallback) | `backend/app/config.py`, `agent/llm.py`, `rag/embedder.py`, `integrations/plaid_client.py`, `mcp/boc_rates.py`, `leaks/boc.py`, `mcp/market.py`, `agent/tools/web_search.py`, `notifications/email.py` | EXACT (in code). Which are live in production: NEEDS DASHBOARD. Finnhub, Tavily, Plaid and SMTP keys are absent from local `.env` |
| LLM models referenced | Groq `openai/gpt-oss-20b` (basic), Groq `openai/gpt-oss-120b` (heavy fallback), `claude-sonnet-4-6` (heavy), Ollama `qwen2.5:7b` (offline) | `backend/app/config.py` | EXACT |
| LLM fallback chain | Groq → Claude → Ollama; Groq HTTP 429 falls straight through to Claude | `backend/agent/llm.py:395-406, 630` | EXACT |
| Model-routing rules | 56 regex "heavy" patterns + 160-char minimum for heavy tier | `backend/agent/routing.py:13,77` (`len(_HEAVY_PATTERNS)` = 56) | EXACT |
| Agent graph | LangGraph, 2 nodes (`agent`, `tools`), conditional loop, max 6 tool loops | `backend/agent/graph.py:23,176-180` | EXACT |
| Agent tools | **14** = 11 core (`search_transactions, aggregate_spending, get_user_financial_profile, search_web, get_financial_insights, get_tfsa_status, get_cash_runway, calculate, run_registered_optimizer, run_osap_plan, run_cash_forecast`) + 3 "MCP" (`convert_currency, get_exchange_rates, get_market_quote`) | `backend/agent/tools/__init__.py:29-263, 296`; `backend/mcp/registry.py` | EXACT |
| "MCP" tools: protocol check | The 3 tools are an **in-process Python registry**. No `mcp` SDK dependency and no MCP server/transport | `backend/pyproject.toml` dependencies; `backend/mcp/registry.py` | EXACT |
| LLM prompts | 2 system-prompt builders (`build_system_prompt`, `build_groq_compact_system_prompt`) + 2 auxiliary LLM calls (memory summarizer, user-profile learning) | `backend/agent/prompts.py:26,117`; `agent/llm.py:530,578`; `agent/user_profile.py:230` | EXACT |
| Auth providers | Supabase Auth with 2 sign-in methods: Google OAuth, email magic link (OTP). Optional `X-API-Key` middleware | `frontend/app/login/page.tsx:31-32,58`; `backend/app/middleware/api_key.py` | EXACT |
| Payment flows | 0 ("stripe" grep hits are merchant-name strings in tests and seed data) | grep over backend/frontend | EXACT |
| Bank CSV formats | 8 named Canadian banks (RBC, TD, CIBC, Scotiabank, BMO, EQ, Tangerine, Simplii) + generic + native FinSight format | `backend/ingest/bank_csv.py:14-22,54-73` | EXACT |
| Money-leak detectors | 4 detector modules (FX markup, duplicates, fees, subscriptions) + 3 letter templates (cancellation, dispute, fee reversal) | `backend/leaks/{fx,duplicates,fees,subscriptions}.py`; `leaks/drafts.py:8-64` | EXACT |
| PII redaction categories | 4: EMAIL, PHONE, ACCOUNT, ETRANSFER | `backend/agent/privacy/redact.py:10-24` | EXACT |
| Tax-rule years shipped | 2 (2025, 2026) | `backend/planning/rules/*.yaml` | EXACT |
| Eval cases | **165** golden questions, **30** smoke (CI subset), **60** retrieval queries (255 lines total) | `wc -l backend/evals/*.jsonl` | EXACT |
| Eval persona | **600** transactions, **47** planted money leaks, 12 months | Ran `build_fixture_transactions(...)` in memory → `transactions 600 planted_leaks 47` | EXACT |
| Chunking | None. One embedding per transaction (no text chunking) | `docs/adr/0003-one-embedding-per-transaction.md`; `rag/indexing.py` | EXACT |
| Embedding model / dims | `voyage-4-large`, 1024 dims (Ollama `nomic-embed-text` 768 offline fallback) | `backend/app/config.py`; migration `n4o5p6q7r8s9_resize_embeddings_1024_voyage.py` | EXACT |
| Embedding batch size | 8 | `backend/rag/indexing.py:18` | EXACT |
| Vector index | pgvector HNSW, cosine, `m = 16`, `ef_construction = 64` | `alembic/versions/f6a7b8c9d0e1_…py:26-29` (recreated at 1024 dims in `n4o5…`) | EXACT |
| Retrieval | Hybrid: pgvector cosine + **ILIKE keyword** match on description/merchant/category, fused by RRF (k = 60). Default top-k = 5, candidate fan-out `max(4k, 20)`, then token-overlap rerank; date/amount filters parsed from the query and applied in SQL | `backend/rag/retriever.py:20,26,95-97,129,158-166`; `rag/rerank.py`; `rag/filters.py` | EXACT |
| Semantic cache | Cosine ≥ 0.97 hit threshold, 64 entries per user, invalidated on category edits. No TTL found | `backend/rag/cache.py:47` | EXACT |
| Monte Carlo forecast | 5,000 simulations default | `backend/planning/forecast.py:16` | EXACT |

## 3. Evaluation and quality figures in the repo

| Metric | Value | Source | Confidence |
|---|---|---|---|
| Stored eval results (smoke, 30 q) | answer_accuracy 1.0, tool_selection_exact 1.0, hallucinated_number_rate 0.0, refusal_accuracy 1.0, recall@5 1.0, nDCG@10 1.0 | `docs/metrics.json` (generated 2026-09-29, "mode": "offline dry run") | EXACT as stored. **Not a model-quality measurement** (see row below) |
| Stored eval results (full, 165 q) | same values, all 1.0 / 0.0 | `docs/metrics.json` | EXACT as stored. **Not a model-quality measurement** |
| Why those scores are 1.0 | The live LLM eval is not wired up (`run.py:349-354` logs "Live LLM eval is not wired up; falling back to --dry-run"). In dry-run the answer is set to the expected value (`run.py:215-219`: "Dry-run claims the expected ground truth"), and retrieval puts the relevant ids at the top of the ranking (`run.py:271-283`). These numbers test the scoring pipeline, not the model or search quality | `backend/evals/run.py` | EXACT |
| Regression gate thresholds | answer accuracy ≥ 0.97, tool exact ≥ 0.97, refusal = 1.00, hallucinated-number rate ≤ 0.00 | `backend/evals/run.py:395-400`; `docs/evals.md` | EXACT |
| Saved eval output files | None committed (`backend/evals/results/` holds only `.gitkeep`) | `ls backend/evals/results` | EXACT |
| CI artifacts | None uploaded (no `upload-artifact` step in `ci.yml`) | `.github/workflows/ci.yml` | EXACT |
| Latency logs | None. No per-request timing is stored or logged; `request_id` middleware only tags log lines | `backend/app/middleware/request_id.py`; grep for `perf_counter/duration/elapsed` = 0 hits in app/agent/rag | EXACT |
| Token/cost logs | None. No usage/token logging, no Langfuse/Sentry/PostHog dependency | grep over `backend/` and `frontend/package.json` | EXACT |
| Load test | k6 script only: 50 VUs × 30 s on `/health` (optional `/chat`), thresholds p95 < 2000 ms, error rate < 5%. **No recorded results** | `infra/load/chat.js` | EXACT (config only) |
| Monthly running cost | "~$7" Railway Hobby; Supabase/Groq/Voyage free tier; Anthropic "a few dollars" | `docs/cost.md` | ESTIMATE (written in docs, not measured) |

## 4. Performance and cost settings in code

| Setting | Value | Source | Confidence |
|---|---|---|---|
| Chat rate limit | 30 requests/min per user (or per IP), 60 s sliding window, HTTP 429 | `backend/app/config.py` (`chat_rate_limit_per_minute`); `app/middleware/chat_rate_limit.py` | EXACT |
| Agent step cap | 6 tool loops | `backend/agent/graph.py:23` | EXACT |
| Max output tokens | Claude 2048; summaries 400; profile learning 500; Ollama ≤ 1024 | `backend/agent/llm.py:94,546,578,473`; `agent/user_profile.py:230` | EXACT |
| Temperature | 0.2 chat, 0.1 summaries | `backend/agent/llm.py:172,472,545` | EXACT |
| Groq context caps | last 8 messages, 1,500 chars per tool result, 2,000 chars user profile | `backend/agent/llm.py:324-326` | EXACT |
| Embedding retries | Voyage: 4 attempts, 22 s wait (free-tier 3 RPM) | `backend/rag/embedder.py:12-13` | EXACT |
| HTTP timeouts | LLM calls 60–180 s; provider health probes 3 s; web search 8–15 s; Bank of Canada 8 s; Yahoo/Finnhub 10 s; Plaid 30 s; SMTP 30 s; JWKS 8 s | `agent/llm.py:193,444,535,591,823,843,864`; `agent/tools/web_search.py:20,50,112`; `mcp/boc_rates.py:16`; `mcp/market.py:17`; `integrations/plaid_client.py:34`; `notifications/email.py:23`; `app/main.py:182` | EXACT |
| DB connection | pool 5 + 10 overflow (Supabase), recycle 1800 s, pre-ping, connect timeout 8 s, fallback probe 4 s | `backend/db/base.py`; `app/config.py` | EXACT |
| Plaid background sync | every 14,400 s (4 h), floor 300 s | `app/config.py`; `integrations/plaid_background.py:36` | EXACT |
| Cache | Semantic retrieval cache (see section 2) | `backend/rag/cache.py` | EXACT |
| Cash-runway window | 90 days | `backend/insights/runway.py:13` | EXACT |

## 5. Production numbers

Not queried. Read-only SQL is in `audit/metrics_queries.sql`; you paste it into your own console. Know these limits before you run it:
- **New users get the demo user's transactions cloned in** on first sign-in (`app/demo_provision.py`), so raw transaction totals are mostly synthetic. Use query 5b/5c.
- There is no last-login column, so "active users" is a proxy.
- Request counts, latency and error rate are **not in the database**. Get them from Railway.

| Metric | Value | Source | Confidence |
|---|---|---|---|
| Total users, signups/month, 30-day active, real transactions, chats, messages, leak findings | not run | `audit/metrics_queries.sql` queries 1–12 | NEEDS DASHBOARD (your DB console) |
| Requests/day, avg & p95 latency, error rate | not stored in DB | Railway metrics / logs | NEEDS DASHBOARD |

## 6. Dashboards to check yourself

| Dashboard | Applies? | Exact metric to copy |
|---|---|---|
| **Supabase** → Authentication → Users | Yes | Total users; filter out the demo user and your test logins. Sign-in provider split (Google vs email) |
| **Supabase** → Reports / Database | Yes | Database size (MB), API request count. Run `audit/metrics_queries.sql` in the SQL editor |
| **Railway** → each service → Metrics | Yes (API + web) | HTTP requests (volume), response time p50/p95/p99, 5xx error rate, uptime window, CPU/RAM. Pick a fixed range, e.g. last 30 days, and note it |
| **Railway** → Usage / Billing | Yes | Actual monthly cost (replaces the "~$7" estimate in `docs/cost.md`) |
| **Anthropic Console** → Usage | Yes | Tokens and $ per month for `claude-sonnet-4-6`; request count (= heavy-tier turns) |
| **Groq Console** → Usage | Yes | Requests and tokens per model (`gpt-oss-20b`, `gpt-oss-120b`). Compare with Anthropic to get the real routing split |
| **Voyage AI dashboard** → Usage | Yes | Total embedding tokens used (against the free allowance) |
| **Plaid Dashboard** | Yes | Environment (Sandbox vs Production) and number of Items linked. If Sandbox, don't call them real bank connections |
| **GitHub** → Insights → Traffic | Yes | Views and unique visitors (14-day window only), clones, stars, forks |
| **GitHub** → Actions | Yes | Pass rate of `CI` on `main` and total workflow runs |
| **GitHub Pages** | Yes (docs site) | No built-in analytics; nothing to copy unless you added one |
| Langfuse | **No**: not integrated (no dependency or calls) | n/a |
| Stripe | **No**: no payment code | n/a |
| Cloudflare | **No**: no Cloudflare config in repo (Railway serves directly) | n/a, unless set up outside the repo |
| App Store Connect / Google Play Console | **No**: web app + PWA manifest (`frontend/app/manifest.ts`); no native app | n/a |

---

## I could not verify

- **Whether CI is green on GitHub.** I did not query the GitHub API. Check Actions.
- **Frontend lint / type-check / build locally.** Not run, because `next build` writes `.next/` and ESLint/tsc may write caches.
- **ruff / mypy locally.** Not run, because they write `.ruff_cache` / `.mypy_cache`. CI runs both.
- **Rerunning the eval harness.** Not run: `evals.run` writes a results file. It makes no paid calls, but its scores are dry-run anyway (section 3).
- **Any live model quality** (real answer accuracy, real hallucination rate, real recall@k). No live-LLM eval exists in the repo, so there is nothing to quote.
- **Latency, throughput, uptime, error rate, cost.** Not logged in code or DB. Use Railway and the provider dashboards.
- **Which optional integrations are live in production** (Plaid environment, Tavily, Finnhub, SMTP digests).
- **Share of chat turns routed to Claude vs Groq.** Routing is in code; actual split needs Anthropic and Groq usage.
- **User, transaction and conversation counts.** Need the SQL file run against production.

## Audit incident (disclosure)

Two commands were run without my environment overrides and imported `backend/db/base.py`, which probes the primary database at import time when it is Supabase (`db/base.py:13-30`). The two commands were `pytest --collect-only` and a one-line import of `agent.routing`. The second logged `Supabase Postgres unreachable (OperationalError). Using local fallback`, so that connection attempt failed. The first may also have attempted a `SELECT 1`. No data was read or written in either case. Every other command ran with all DB/API variables overridden to dead values. This import-time probe is also a footgun for anyone running tests with a real `.env`.

---

## Top 5 resume-worthy numbers

1. **335 automated backend tests, all passing**, plus CI gating on ruff, strict mypy, pytest and an eval gate. **EXACT** (verified locally today; matches `docs/metrics.json`).
2. **78 REST endpoints across 17 FastAPI routers**, backed by **13 Postgres tables / 17 Alembic migrations** with pgvector HNSW (1024-dim). **EXACT**.
3. **LangGraph agent with 14 tools**, two-tier routing (Groq ↔ Claude, 56 routing rules) and a Groq → Claude → Ollama fallback chain. **EXACT**. Say "tool registry", not "MCP server".
4. **Eval harness: 165 golden questions + 60 retrieval queries over a 600-transaction persona with 47 planted money leaks, gated at ≥ 97% in CI and the Docker build.** **EXACT** for the counts and thresholds. Do not attach the 100% scores (see below).
5. **Solo build: 166 commits, 3 tagged releases, ~34k lines (23.3k Python + 11.2k TypeScript), May–Sep 2026.** **EXACT**. Any user or traffic number to pair with this **needs your confirmation** from Supabase/Railway.

## 3 numbers not to claim

1. **"100% answer accuracy / 0% hallucination / recall@5 = 1.0".** These come from a dry run in which the harness feeds the ground truth back as the answer and the ranking (`backend/evals/run.py:215-219, 271-283, 349-354`). They prove the scoring plumbing works. They say nothing about the model or search quality.
2. **Any "transactions processed" total read straight from production.** Every new user gets the demo dataset cloned in (`backend/app/demo_provision.py`), and `seed_full.py` loads a synthetic year. Quote only the non-demo count from query 5b/5c, and only if it's material.
3. **"3 MCP integrations" or "Model Context Protocol server".** The `mcp/` package is an in-process function registry with no MCP SDK or transport. Related: don't say "Postgres full-text search". The keyword half of hybrid search is `ILIKE` (`rag/retriever.py:95-97`), even though `docs/evals.md` says full-text. Also don't quote "~$7/month" as measured cost; it's an estimate in `docs/cost.md`.
