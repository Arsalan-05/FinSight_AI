# FinSight AI

Personal finance intelligence — transaction ingest, pgvector search, and a stateful advisor grounded in your data. Canadian bank CSV import, optional Plaid sync, budgets, and spending insights.

**Status:** v1.4 completed June 30, 2026 · owned 100% by Arsalan Amir Ali

Runs locally with Ollama. Supabase handles Google login.

## Quick start

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
docker compose up -d db
./infra/supabase/setup-e2e.sh   # or: cd backend && uv run alembic upgrade head

cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

**Prerequisites:** [Ollama](https://ollama.com) (`llama3.2`, `nomic-embed-text`), [uv](https://docs.astral.sh/uv/), Node 20+.

Full reference: **[DOCUMENTATION.md](./DOCUMENTATION.md)** · **[infra/railway/DEPLOY.md](infra/railway/DEPLOY.md)** · **[DEV.md](./DEV.md)**

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama

## License & ownership

Copyright (c) 2026 **Arsalan Amir Ali** — 100% owner. MIT License — see [LICENSE](./LICENSE) and [DOCUMENTATION.md §20](./DOCUMENTATION.md#20-rights-license--ownership).
