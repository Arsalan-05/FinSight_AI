# CLAUDE.md

Guidance for AI coding assistants working in this repository.

**Full project documentation:** [DOCUMENTATION.md](./DOCUMENTATION.md)

## Project

FinSight AI — personal finance intelligence agent. FastAPI backend, Next.js frontend, PostgreSQL + pgvector, LangGraph ReAct agent, Supabase Google OAuth.

## Repo layout

```
backend/   FastAPI, LangGraph agent, RAG, MCP tools, Alembic migrations
frontend/  Next.js chat UI + dashboards
infra/     Docker Compose, Supabase setup scripts
```

## Dev commands

```bash
docker compose up --build                    # full stack
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

cd backend && uv run pytest -q
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run mypy app/ agent/ db/ rag/ insights/
cd frontend && npm run lint && npm run type-check
```

## Conventions

- Python package manager: `uv` (not pip)
- Backend code under `backend/app/`, `backend/agent/`, `backend/rag/`, `backend/db/`
- FastAPI DI for DB sessions — do not instantiate inside route handlers
- LangGraph state in TypedDict — new fields go there
- MCP tools: one file per server in `backend/mcp/`
- Default LLM: Ollama `llama3.2`; optional Anthropic `claude-sonnet-4-6`
- Secrets in `.env` only — never commit
