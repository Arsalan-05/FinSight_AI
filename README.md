# FinSight AI

My personal finance intelligence app — I ingest transactions, build a pgvector knowledge base, and chat with a stateful agent that answers spending questions from grounded tool calls. Every conversation is saved to Postgres.

**Private portfolio project** — runs locally with Ollama or optionally with Claude/Voyage APIs.

## Quick start

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
./infra/supabase/setup-e2e.sh

cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

**Prerequisites:** [Ollama](https://ollama.com) (`llama3.2`, `nomic-embed-text`), [uv](https://docs.astral.sh/uv/), Node 20+.

Full startup steps, architecture, and API reference: **[DOCUMENTATION.md](./DOCUMENTATION.md)**

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama

## License

Private — not licensed for redistribution.
