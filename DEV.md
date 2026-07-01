# Developer guide

Project reference: [DOCUMENTATION.md](./DOCUMENTATION.md)

## Layout

```
backend/   FastAPI, LangGraph agent, RAG, MCP tools, Alembic migrations
frontend/  Next.js UI + dashboards
infra/     Docker Compose, Supabase setup scripts
scripts/   Local bootstrap helpers
```

## Commands

```bash
docker compose up --build
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

cd backend && uv run pytest -q
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run mypy app/ agent/ db/ rag/ insights/
cd frontend && npm run lint && npm run type-check
```

## Conventions

- Python package manager: `uv`
- Backend code under `backend/app/`, `backend/agent/`, `backend/rag/`, `backend/db/`
- FastAPI DI for DB sessions — do not instantiate inside route handlers
- LangGraph state in TypedDict — new fields go there
- MCP tools: one file per server in `backend/mcp/`
- Default LLM: Ollama `qwen2.5:7b` (free local); Groq free tier on Render; Anthropic optional paid
- Secrets in `.env` only — never commit
