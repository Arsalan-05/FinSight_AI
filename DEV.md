# Developer guide

**Production is the product.** Local is the workshop — use it only when coding, testing, or debugging.

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
cd backend && uv run pytest -q
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run mypy app/ agent/ db/ rag/ insights/
cd frontend && npm run lint && npm run type-check

# Docker full stack (optional)
docker compose up --build
```

## AI stack

| Layer | Default | Fallback |
|-------|---------|----------|
| Chat | Groq `llama-3.1-8b-instant` (`GROQ_MODEL`) | Ollama `qwen2.5:7b` if no `GROQ_API_KEY` |
| Embeddings | Voyage `voyage-4-large` | Ollama `nomic-embed-text` if no `VOYAGE_API_KEY` |

Set `GROQ_API_KEY`, `GROQ_MODEL`, and `VOYAGE_API_KEY` in `.env` (local) and on the Railway **API** service. Frontend and Supabase do not need Groq/Voyage keys.

**Why 8B not 70B:** Better free-tier rate limits for the advisor agent; sufficient for personal finance Q&A.

## Deploy after changes

```bash
git push origin main
# Railway: both services auto-redeploy from GitHub (if connected)
# Or: Dashboard → service → Redeploy
curl https://finsight-api-production-2aee.up.railway.app/capabilities
```

**v1.5.1 backend paths:** `backend/agent/scope.py`, `backend/agent/llm.py` (`call_llm_plain`), `backend/agent/prompts.py`  
**v1.5.1 frontend paths:** `frontend/lib/chat-stream-manager.ts`, `frontend/contexts/ChatStreamContext.tsx`

**What deploys where:**

| Change type | Railway frontend | Railway API | Supabase |
|-------------|------------------|-------------|----------|
| Frontend UI (pages, chat links) | ✅ | — | — |
| Backend API / agent / search | — | ✅ | — |
| `GROQ_MODEL` env var | — | ✅ API only | — |
| Database schema | — | migrations on deploy | — |
| `NEXT_PUBLIC_*` change | ✅ rebuild required | — | — |

- Python package manager: `uv`
- Backend code under `backend/app/`, `backend/agent/`, `backend/rag/`, `backend/db/`
- FastAPI DI for DB sessions — do not instantiate inside route handlers
- LangGraph state in TypedDict — new fields go there
- MCP tools: one file per server in `backend/mcp/`
- Secrets in `.env` only — never commit
- Use `127.0.0.1` not `localhost` for `NEXT_PUBLIC_API_URL` (macOS IPv6)
- Cap `DB_POOL_SIZE=2` locally — Supabase session pooler shares ~15 slots with Railway

## Conventions
