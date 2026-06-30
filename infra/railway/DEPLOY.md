# Railway deployment — FinSight AI

Deploy as **two Railway services** from this monorepo (private repo is fine).

## 1. Backend (API)

1. [Railway](https://railway.app) → New Project → Deploy from GitHub → select this repo.
2. Service settings → **Root Directory**: `backend`
3. Railway reads `backend/railway.toml` and `backend/Dockerfile`.
4. Set variables:

| Variable | Value |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase **pooler** URL (`?pgbouncer=true` for transaction mode) |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `REQUIRE_AUTH` | `true` |
| `LLM_PROVIDER` | `anthropic` (recommended for production) |
| `ANTHROPIC_API_KEY` | your key |
| `EMBEDDING_PROVIDER` | `voyage` or `ollama` |
| `VOYAGE_API_KEY` | if using Voyage |
| `CORS_ORIGINS` | `https://<your-frontend>.up.railway.app` |
| `CHAT_RATE_LIMIT_PER_MINUTE` | `30` |
| `FINNHUB_API_KEY` | optional — live stock quotes |
| `LOG_LEVEL` | `INFO` |

5. Generate domain → note API URL (e.g. `https://finsight-api.up.railway.app`).

**Ollama on Railway:** not supported — use Anthropic for LLM in production.

## 2. Frontend

1. Add service → same repo → **Root Directory**: `frontend`
2. Build args / variables:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | backend Railway URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

3. Generate domain → add this URL to backend `CORS_ORIGINS`.

## 3. Database

- Use **Supabase hosted Postgres** (not Railway Postgres) for pgvector + auth alignment.
- Run migrations: `cd backend && uv run alembic upgrade head` against production `DATABASE_URL`.
- Optional RLS: `psql $DATABASE_URL -f infra/supabase/03_rls_policies.sql`

## 4. Supabase Auth redirect URLs

In Supabase Dashboard → Authentication → URL Configuration:

- Site URL: `https://<frontend>.up.railway.app`
- Redirect URLs: `https://<frontend>.up.railway.app/**`, `http://localhost:3000/**`

## 5. Verify

```bash
curl https://<api>/health
curl https://<api>/health/ready
```

Open frontend → sign in → dashboard loads.

## Local vs production

| | Local | Production |
|---|--------|------------|
| LLM | Ollama | Anthropic |
| DB | Docker or Supabase | Supabase pooler |
| CORS | localhost auto | `CORS_ORIGINS` env |
| Logs | text | JSON (`ENVIRONMENT=production`) |
| Market quotes | Yahoo (no key) | Finnhub + Yahoo fallback |
