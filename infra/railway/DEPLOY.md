# Railway deployment — FinSight AI

**Production is Railway-only:** two services from this monorepo + Supabase for DB/auth.

```
User → Railway frontend (Next.js) → Railway API (FastAPI) → Supabase + Groq + Voyage
```

## 1. Backend (`finsight-api`)

1. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub** → select `FinSight_AI`.
2. Service settings → **Root Directory**: `backend`
3. Railway reads [`backend/railway.toml`](../../backend/railway.toml) and [`backend/Dockerfile`](../../backend/Dockerfile).
4. **Networking → Generate domain** → copy API URL (e.g. `https://finsight-api-xxxx.up.railway.app`).
5. Set variables (Variables tab):

| Variable | Value |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase **session pooler** URL (port **5432**, `?sslmode=require`) |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `REQUIRE_AUTH` | `true` |
| `DATABASE_FALLBACK_ENABLED` | `false` |
| `LLM_PROVIDER` | `groq` |
| `GROQ_API_KEY` | from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `EMBEDDING_PROVIDER` | `voyage` |
| `VOYAGE_API_KEY` | from [dash.voyageai.com](https://dash.voyageai.com) |
| `VOYAGE_MODEL` | `voyage-4-large` |
| `CORS_ORIGINS` | `https://<your-frontend>.up.railway.app` (set after step 2) |
| `CHAT_RATE_LIMIT_PER_MINUTE` | `30` |
| `BETA_ALLOWED_EMAILS` | comma-separated invite list (empty = open) |
| `FINNHUB_API_KEY` | optional |
| `PLAID_CLIENT_ID` / `PLAID_SECRET` / `PLAID_ENV` | optional |
| `PLAID_TOKEN_ENCRYPTION_KEY` | optional Fernet key |
| `PLAID_WEBHOOK_SECRET` | optional |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | optional weekly digest |
| `LOG_LEVEL` | `INFO` |

6. Redeploy after adding vars. Migrations run on container start (`db.migrate`).

**Verify:**

```bash
curl https://<api>.up.railway.app/health
curl https://<api>.up.railway.app/health/ready
curl https://<api>.up.railway.app/capabilities
```

## 2. Frontend (`finsight-web`)

1. Same Railway project → **Add service** → same GitHub repo.
2. **Root Directory**: `frontend`
3. Railway reads [`frontend/railway.toml`](../../frontend/railway.toml) and [`frontend/Dockerfile`](../../frontend/Dockerfile).
4. Set variables **before the first successful build** (baked into Next.js at build time):

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | backend URL from step 1 (no trailing slash) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

5. **Networking → Generate domain** → this is your **app URL**.
6. Go back to backend → set `CORS_ORIGINS` to the frontend URL → **Redeploy** backend.

If you change any `NEXT_PUBLIC_*` value later, trigger a **new frontend rebuild** (Redeploy).

## 3. Database

- Use **Supabase hosted Postgres** (not Railway Postgres) for pgvector + auth alignment.
- Migrations auto-run on API deploy; or locally: `cd backend && uv run alembic upgrade head` against production `DATABASE_URL`.

## 4. Supabase Auth redirect URLs

Dashboard → **Authentication → URL Configuration**:

- **Site URL:** `https://<frontend>.up.railway.app`
- **Redirect URLs:**
  - `https://<frontend>.up.railway.app/**`
  - `http://localhost:3000/**` (local dev)
  - `http://127.0.0.1:3000/**` (local dev)

Remove old Vercel URLs after cutover.

## 5. GitHub Pages landing (optional)

Edit [`docs/config.js`](../../docs/config.js):

```js
window.FINSIGHT_APP_URL = "https://<frontend>.up.railway.app";
```

## 6. End-to-end checklist

- [ ] `curl` health + ready + capabilities succeed
- [ ] Open frontend → Google sign-in works
- [ ] Dashboard loads accounts / transactions
- [ ] Chat returns a finance answer
- [ ] Search / reindex works (Voyage key on API)
- [ ] After 24h stable: delete Vercel project + Render API service

## 7. Invite-only beta

Set `BETA_ALLOWED_EMAILS=you@example.com` on the backend. Unlisted emails get HTTP 403.

Plaid webhook (if used): `https://<api>/integrations/plaid/webhook`

## Local vs production

| | Local | Production (Railway) |
|---|--------|----------------------|
| LLM | Groq | Groq |
| DB | Docker or Supabase | Supabase pooler |
| CORS | localhost auto | `CORS_ORIGINS` env |
| Frontend | `npm run dev` | Docker / Railway |
| Cold starts | none | none (paid Railway — no free-tier sleep) |
