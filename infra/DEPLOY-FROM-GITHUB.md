# Deploy FinSight from GitHub (Railway + Supabase)

FinSight is a **full-stack app** (Next.js + FastAPI + PostgreSQL + agent). **GitHub Pages cannot run it** — Pages only serves static HTML/CSS/JS.

What you get:

| URL | What it is |
|-----|------------|
| `https://arsalan-05.github.io/FinSight_AI/` | **One-page** marketing site (`docs/index.html`) — optional |
| `https://<your-frontend>.up.railway.app` | **The real app** — login, chat, dashboard |

Users visit **one app URL** (Railway frontend).

---

## What you need

1. **GitHub** — this repo
2. **Supabase** — Google auth + hosted Postgres ([supabase.com](https://supabase.com))
3. **Railway** — backend + frontend ([railway.app](https://railway.app)) — paid plan recommended (no cold starts)
4. **Groq** + **Voyage** API keys (free tiers)

Full detail: **[infra/railway/DEPLOY.md](./railway/DEPLOY.md)**

---

## Step 1 — Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. **Authentication → Providers** → enable Google.
3. **Authentication → URL Configuration** — add redirect URLs after you have Railway URLs (Step 4).
4. **Settings → Database** → copy the **session pooler** URL (port **5432**) for `DATABASE_URL`.
5. Enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
6. Migrations run automatically on Railway API deploy (or locally against production `DATABASE_URL`).

---

## Step 2 — Deploy backend (Railway)

1. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select `FinSight_AI`.
2. Set **Root Directory** to `backend`.
3. Add environment variables (see [railway/DEPLOY.md](./railway/DEPLOY.md) §1).
4. **Settings → Networking → Generate domain** → e.g. `https://finsight-api.up.railway.app`.
5. Verify: `curl https://finsight-api.up.railway.app/health`

---

## Step 3 — Deploy frontend (Railway)

1. Same Railway project → **Add service** → same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Variables (**set before first build**):

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | backend URL from Step 2 |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

4. **Generate domain** → e.g. `https://finsight.up.railway.app` — **this is your one app URL**.
5. Backend → set `CORS_ORIGINS` to this frontend URL → redeploy API.

---

## Step 4 — Supabase redirect URLs

In Supabase → **Authentication → URL Configuration**:

- **Site URL:** `https://finsight.up.railway.app`
- **Redirect URLs:**
  - `https://finsight.up.railway.app/**`
  - `http://localhost:3000/**`
  - `http://127.0.0.1:3000/**`

---

## Step 5 — GitHub Pages (optional landing)

1. GitHub repo → **Settings → Pages → Source:** **GitHub Actions**
2. Push to `main` — workflow `.github/workflows/pages.yml` deploys `docs/`.
3. Site: `https://arsalan-05.github.io/FinSight_AI/`
4. Edit `docs/config.js`:
   ```js
   window.FINSIGHT_APP_URL = "https://finsight.up.railway.app";
   ```

---

## Step 6 — Verify end-to-end

```bash
curl https://finsight-api.up.railway.app/health/ready
curl https://finsight-api.up.railway.app/capabilities
```

1. Open `https://finsight.up.railway.app`
2. Sign in with Google
3. Dashboard loads data
4. Chat responds (needs `GROQ_API_KEY` on backend)

---

## One URL summary

| Role | Host |
|------|------|
| App users open | Railway frontend |
| API | Railway backend |
| DB + Auth | Supabase |
| Optional marketing | GitHub Pages |

---

## Retiring Vercel / Render

After Railway is verified, delete old Vercel and Render projects so traffic and env keys are not split. See [DEPLOY-FREE.md](./DEPLOY-FREE.md) (legacy notice only).
