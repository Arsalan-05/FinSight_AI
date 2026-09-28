# Developer guide

Production is where FinSight runs; local is for coding, testing and debugging.

| | Production | Local |
|--|------------|-------|
| App | https://finsightai-production-43d0.up.railway.app | http://localhost:3000 |
| API | https://finsight-api-production-2aee.up.railway.app | http://127.0.0.1:8000 |
| When | Daily use, demos | `git pull` → edit → test → push |

Full reference: [DOCUMENTATION.md](./DOCUMENTATION.md)  
Deploy: [infra/railway/DEPLOY.md](./infra/railway/DEPLOY.md)

## Layout

```
backend/   FastAPI, LangGraph agent, RAG, MCP tools, Alembic migrations
frontend/  Next.js UI + dashboards
infra/     Docker Compose, Supabase setup scripts, Railway deploy guides
scripts/   Local bootstrap helpers
```

## Commands (local workshop)

```bash
# Start local stack (two terminals)
cd backend && set -a && source ../.env && set +a
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm run dev

# Quality gate before push
cd backend && uv run ruff check . && uv run ruff format --check .
cd backend && uv run mypy app/ agent/ db/ rag/ insights/
cd backend && uv run pytest -q
cd backend && uv run python -m evals.run --subset full --dry-run
cd frontend && npm run lint && npm run type-check && npm run build

# Docker full stack (optional)
docker compose up --build
```

## AI stack

| Layer | Default | Fallback |
|-------|---------|----------|
| Chat **basic** | Groq `openai/gpt-oss-20b` | Ollama `qwen2.5:7b` if no Groq key |
| Chat **heavy** | Claude `claude-sonnet-4-6` (`ANTHROPIC_API_KEY`) | Groq `openai/gpt-oss-120b`, then Ollama |
| Embeddings | Voyage `voyage-4-large` (1024-d) | Ollama `nomic-embed-text` (768-d) if no Voyage key |

Set `GROQ_API_KEY`, `LLM_ROUTING_ENABLED=true`, optional `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`, and `VOYAGE_API_KEY` in `.env` (local) and on the Railway **API** service.

**Why tiered:** most questions are lookups and stay on Groq. Planning, coaching, leaks and tax go to Claude (ADR 0005). A Groq 429 falls through to Claude.

## Deploy after changes

```bash
git push origin main
# Railway: both services auto-redeploy from GitHub (if connected)
# Or: Dashboard → service → Redeploy
curl https://finsight-api-production-2aee.up.railway.app/capabilities
```

**Where chat lives:** `backend/agent/` (routing, graph, runner, prompts, guardrails), `backend/app/routers/chat.py`, `frontend/lib/chat-stream-manager.ts`, `frontend/contexts/ChatStreamContext.tsx`, `frontend/app/chat/page.tsx`

**What deploys where:**

| Change type | Railway frontend | Railway API | Supabase |
|-------------|------------------|-------------|----------|
| Frontend UI (pages, chat links) | yes | — | — |
| Backend API / agent / search | — | yes | — |
| `GROQ_MODEL` env var | — | yes | — |
| Database schema | — | migrations on deploy | — |
| `NEXT_PUBLIC_*` change | rebuild required | — | — |

## Conventions

- Python package manager: `uv`
- Backend code under `backend/app/`, `backend/agent/`, `backend/rag/`, `backend/db/`
- FastAPI DI for DB sessions — do not instantiate inside route handlers
- LangGraph state in TypedDict — new fields go there
- MCP tools: one file per server in `backend/mcp/`
- Secrets in `.env` only — never commit
- Use `127.0.0.1` not `localhost` for `NEXT_PUBLIC_API_URL` (macOS IPv6)
- Cap `DB_POOL_SIZE=2` locally — Supabase session pooler shares ~15 slots with Railway
