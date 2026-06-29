# FinSight AI

**Author:** Arsalan Amir Ali  
**Status:** ✅ COMPLETE — portfolio-ready, tested, documented, published.

My personal finance app — I ingest transactions, build a pgvector knowledge base, and chat with a stateful agent that answers spending questions from grounded tool calls. Every conversation is saved to Postgres with pin, rename, and delete.

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

Full reference including the completion checklist: **[DOCUMENTATION.md](./DOCUMENTATION.md)**

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama

## License

Private — not licensed for redistribution.
