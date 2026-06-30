# FinSight AI

**Author:** Arsalan Amir Ali  
**Status:** ✅ **PRIVATE · PRODUCTION-GRADE** — fully built, tested, deploy-ready. Repo stays private.

My personal finance intelligence system — not a demo. I ingest transactions, embed them in pgvector, and run a stateful agent that learns my spending patterns, searches the web for current facts, and answers from grounded tool calls. Live market data, BoC FX, Supabase auth, Railway configs included — deploy when I want, keep the repo private.

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

Full reference including deploy guide: **[DOCUMENTATION.md](./DOCUMENTATION.md)** · **[infra/railway/DEPLOY.md](infra/railway/DEPLOY.md)**

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama

## License

Private — not licensed for redistribution.
