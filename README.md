# FinSight AI

**A Canadian personal-finance agent that finds money you're losing, proves every number it shows, and never lets the LLM do the math.**

**Status:** complete · v2.0.0 · [MIT License](./LICENSE) · built and maintained by Arsalan Amir Ali

| | URL |
|--|-----|
| App | https://finsightai-production-43d0.up.railway.app |
| API | https://finsight-api-production-2aee.up.railway.app ([`/docs`](https://finsight-api-production-2aee.up.railway.app/docs)) |

Access is invite-only (Google or email sign-in); new accounts get demo data so every page has something to show.

## What it does

- **Advisor chat.** Ask "how much did I spend on dining last month?" or "can I afford a $1,600 laptop by December?". Every dollar in the reply is tagged with the tool result it came from, and a numeric guardrail strips any amount the data can't back up.
- **Money leaks.** Detects FX markups, duplicate charges, bank fees and subscriptions whose price crept up, then drafts the cancellation or dispute letter.
- **Canadian planning.** TFSA / RRSP / FHSA contribution order, OSAP estimates, a student tax helper and a seedable Monte Carlo forecast, all computed from year-specific rules in YAML.
- **Search and insights.** Hybrid keyword + vector search over transactions, a weekly brief, budgets, goals, cash runway and alerts.
- **Your data stays yours.** Full JSON export, one-click account deletion, audit log, PII redaction before any LLM call, and Postgres row-level security.

## How it works

```
Next.js (Railway) ──/backend proxy──▶ FastAPI (Railway) ──▶ Supabase Postgres + pgvector
                                          │
                                          ├── LangGraph agent ── Groq gpt-oss-20b  (basic turns)
                                          │                  └─ Claude Sonnet 4.6 (planning / coaching)
                                          ├── deterministic engines: leaks, planning, runway, calculate
                                          └── Voyage voyage-4-large embeddings (1024-d)
```

Python computes; the model picks tools and explains. See [`docs/architecture.md`](./docs/architecture.md) and the [ADRs](./docs/adr/).

## Stack

Python 3.11 · FastAPI · LangGraph · SQLAlchemy 2.1 · psycopg 3 · PostgreSQL + pgvector · Next.js 16 · React 19 · TypeScript · Tailwind 4 · Supabase Auth · Groq · Anthropic · Voyage · Docker · Railway · GitHub Actions

## Run it locally

```bash
cp .env.example .env                      # add GROQ_API_KEY, VOYAGE_API_KEY, Supabase keys
cp frontend/.env.local.example frontend/.env.local

docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

cd frontend && npm ci && npm run dev      # http://localhost:3000
```

`ANTHROPIC_API_KEY` is optional: without it, heavy turns use Groq `gpt-oss-120b`.

## Quality

| Check | Command |
|-------|---------|
| Lint, format, strict types | `uv run ruff check . && uv run ruff format --check . && uv run mypy app/ agent/ db/ rag/ insights/` |
| Backend tests | `uv run pytest -q` |
| Eval gate (165 questions) | `uv run python -m evals.run --subset full --dry-run` |
| Frontend | `npm run lint && npm run type-check && npm run build` |

All of these run in CI on every push. Current numbers are in [`docs/metrics.json`](./docs/metrics.json).

## Documentation

Start with [DOCUMENTATION.md](./DOCUMENTATION.md): features, configuration, data model, operations and known limits, with links to the detailed docs in [`docs/`](./docs/).

## License

Copyright (c) 2026 Arsalan Amir Ali. Released under the [MIT License](./LICENSE).
