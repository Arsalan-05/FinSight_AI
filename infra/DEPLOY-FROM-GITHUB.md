# Deploy FinSight from GitHub (one live URL)

FinSight is a **full-stack app** (Next.js + FastAPI + PostgreSQL + agent). **GitHub Pages cannot run it** — Pages only serves static HTML/CSS/JS. There is no database, API, or login on Pages.

What you get:

| URL | What it is |
|-----|------------|
| `https://arsalan-05.github.io/FinSight_AI/` | **One-page** marketing site (`docs/index.html`) |
| `https://<your-frontend>.up.railway.app` | **The real app** — login, chat, dashboard, everything |

Users visit **one app URL** (Railway frontend). GitHub Pages is optional marketing.

---

## What you need (free tiers available)

1. **GitHub** — this repo (already have)
2. **Supabase** — Google auth + hosted Postgres ([supabase.com](https://supabase.com))
3. **Railway** — backend + frontend ([railway.app](https://railway.app))
4. **Anthropic API key** — optional paid alternative to Groq

---

## Step 1 — Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. **Authentication → Providers** → enable Google.
3. **Authentication → URL Configuration** — add redirect URLs after you have Railway URLs (Step 4).
4. **Settings → Database** → copy the **connection pooler** URL for `DATABASE_URL`.
5. Run migrations against production DB:
   ```bash
   cd backend
   export DATABASE_URL="postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"
   uv run alembic upgrade head
   ```

---

## Step 2 — Deploy backend (Railway)

1. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select `FinSight_AI`.
2. Add a service → set **Root Directory** to `backend`.
3. Add environment variables:

| Variable | Value |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase pooler URL |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `REQUIRE_AUTH` | `true` |
| `LLM_PROVIDER` | `groq` |
| `GROQ_API_KEY` | free at [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `EMBEDDING_PROVIDER` | `voyage` |
| `VOYAGE_API_KEY` | from [dash.voyageai.com](https://dash.voyageai.com) |
| `ANTHROPIC_API_KEY` | optional paid alternative |
| `CORS_ORIGINS` | `https://<frontend-url>.up.railway.app` (fill after Step 3) |
| `BETA_ALLOWED_EMAILS` | `your@gmail.com` (invite-only) |

4. **Settings → Networking → Generate domain** → copy URL, e.g. `https://finsight-api.up.railway.app`.
5. Verify: `curl https://finsight-api.up.railway.app/health`

---

## Step 3 — Deploy frontend (Railway)

1. Same Railway project → **Add service** → same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Variables:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | backend URL from Step 2 |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

4. **Generate domain** → e.g. `https://finsight.up.railway.app` — **this is your one app URL**.
5. Go back to backend → set `CORS_ORIGINS` to this frontend URL → redeploy backend.

---

## Step 4 — Supabase redirect URLs

In Supabase → **Authentication → URL Configuration**:

- **Site URL:** `https://finsight.up.railway.app`
- **Redirect URLs:**
  - `https://finsight.up.railway.app/**`
  - `http://localhost:3000/**` (keep for local dev)

---

## Step 5 — GitHub Pages (optional landing)

1. GitHub repo → **Settings → Pages → Source:** **GitHub Actions**
2. Push to `main` — workflow `.github/workflows/pages.yml` deploys `docs/`.
3. Site: `https://arsalan-05.github.io/FinSight_AI/`
4. Edit `docs/config.js`:
   ```js
   window.FINSIGHT_APP_URL = "https://finsight.up.railway.app";
   ```
5. Push again — **Open FinSight** button on the landing page goes to your live app.

---

## Step 6 — Verify end-to-end

```bash
curl https://finsight-api.up.railway.app/health/ready
```

1. Open `https://finsight.up.railway.app`
2. Sign in with Google
3. Dashboard loads data
4. Chat responds (needs `GROQ_API_KEY` on backend)

---

## One URL summary

| Goal | Solution |
|------|----------|
| **One URL for the full app** | Railway frontend domain only |
| **One GitHub Pages site** | `docs/index.html` (home + features + privacy in one page) |
| **Deploy triggered from GitHub** | Railway watches `main` — push to deploy |
| **Cannot do on Pages alone** | API, Postgres, agent, Plaid, auth |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| CORS error | Add frontend URL to backend `CORS_ORIGINS` |
| Google login fails | Add Railway URL to Supabase redirect URLs |
| Empty dashboard | Run `alembic upgrade head` on production DB |
| Chat no response | Set `GROQ_API_KEY`, `GROQ_MODEL=llama-3.1-8b-instant`, redeploy backend |
| 403 on login | Add your email to `BETA_ALLOWED_EMAILS` |

More detail: [infra/railway/DEPLOY.md](./railway/DEPLOY.md)
