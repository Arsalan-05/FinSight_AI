# FinSight AI — Deploy

Production runs on **Railway** (frontend + API) + **Supabase** (Postgres + Auth).

Custom domain (e.g. `finsightai.ca`) should CNAME to Railway once purchased. Until then use the Railway URLs from the live environment checklist.

## Services

| Service | Root | Role |
|---------|------|------|
| `finsight-web` | `frontend/` | Next.js |
| `finsight-api` | `backend/` | FastAPI |

## Required env (API)

```
ENVIRONMENT=production
DATABASE_URL=<supabase session pooler :5432>
SUPABASE_URL=https://<project-ref>.supabase.co
REQUIRE_AUTH=true
DATABASE_FALLBACK_ENABLED=false
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
GROQ_HEAVY_MODEL=llama-3.3-70b-versatile
LLM_ROUTING_ENABLED=true
ANTHROPIC_API_KEY=...          # optional — enables Claude for heavy turns
ANTHROPIC_MODEL=claude-sonnet-4-6
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=...
CORS_ORIGINS=https://<your-frontend-host>
BETA_ALLOWED_EMAILS=...
```

Never commit project refs, service-role keys, or Plaid secrets. Prefer placeholders in docs.

## Required env (frontend)

```
NEXT_PUBLIC_API_URL=/backend
API_PROXY_TARGET=https://<api-host>
NEXT_PUBLIC_SITE_URL=https://<frontend-host>
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

`NEXT_PUBLIC_API_URL=/backend` makes the browser call the **same website host** only. Next.js rewrites `/backend/*` to `API_PROXY_TARGET`. This avoids Safari/cross-origin failures when the API is on a different Railway hostname.

## Supabase Auth redirects

```
https://<frontend-host>/**
http://localhost:3000/**
http://127.0.0.1:3000/**
```

## Local (optional)

Ollama is **optional** — only needed when Groq/Voyage keys are unset for offline work.

```bash
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

Full guides: [`infra/railway/DEPLOY.md`](../infra/railway/DEPLOY.md) · [`infra/RAILWAY-CHECKLIST.md`](../infra/RAILWAY-CHECKLIST.md)

## Staging → prod (v2.0)

CI: lint → types → tests → eval smoke → Docker build → Railway staging → smoke → promote.

Weekly keep-alive Action pings `/health` so free-tier projects do not pause.
