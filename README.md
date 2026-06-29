# FinSight AI

Personal finance intelligence agent — ingest transactions, build a RAG knowledge base with pgvector, and chat with a stateful LangGraph agent that answers spending questions with grounded tool calls.

**Private / portfolio project** — runs locally with free Ollama models or optionally with Claude/Voyage APIs.

## Quick start

```bash
cp .env.example .env          # configure Supabase + DATABASE_URL
./infra/supabase/setup-e2e.sh # or: docker compose up -d db && alembic upgrade head && seed

cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

**Prerequisites:** [Ollama](https://ollama.com) (`llama3.2`, `nomic-embed-text`), [uv](https://docs.astral.sh/uv/), Node 20+.

## Documentation

**[DOCUMENTATION.md](./DOCUMENTATION.md)** — complete project reference:

- Architecture, database schema, API reference
- Supabase auth setup, environment variables
- RAG pipeline, LangGraph agent, Canadian bank features
- Frontend pages, testing, troubleshooting
- Interview guide and demo script

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama / Claude

## License

Private — not licensed for redistribution.
