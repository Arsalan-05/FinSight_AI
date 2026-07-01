# Deploy FinSight for $0 (Vercel + Render + Supabase)

One live app URL on **Vercel**. Backend on **Render free tier**. Database + auth on **Supabase free tier**.

| Service | Role | Cost |
|---------|------|------|
| [Vercel](https://vercel.com) | Next.js frontend | Free |
| [Render](https://render.com) | FastAPI backend | Free (sleeps after 15 min idle) |
| [Supabase](https://supabase.com) | Postgres + Google login | Free |
| [GitHub Pages](https://pages.github.com) | Optional landing page | Free |

**Your app URL:** `https://<project>.vercel.app` (one link for everything)

> **Chat on free cloud:** Ollama does not run on Render. Dashboard, login, transactions, and **chat history** are free. For new AI replies use **local Ollama** (`qwen2.5:7b`). Optional paid: `ANTHROPIC_API_KEY` on Render.

---

## One-click deploy buttons

After pushing this repo to GitHub:

### 1. Backend (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Arsalan-05/FinSight_AI)

Uses [`render.yaml`](../render.yaml) in the repo root.

### 2. Frontend (Vercel)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FArsalan-05%2FFinSight_AI&root-directory=frontend&env=NEXT_PUBLIC_API_URL,NEXT_PUBLIC_SUPABASE_URL,NEXT_PUBLIC_SUPABASE_ANON_KEY)

Set **Root Directory** to `frontend` if not auto-detected.

---

## Step-by-step (first time)

### A — Supabase (10 min)

1. [supabase.com](https://supabase.com) → **New project** (free).
2. **Authentication → Providers** → enable **Google** (OAuth client from Google Cloud Console).
3. **Settings → API** → copy:
   - Project URL → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. **Settings → Database** → copy **Session pooler** URI (port **5432**, not 6543) → `DATABASE_URL`  
   Format: `postgresql://postgres.<ref>:<password>@aws-*-*.pooler.supabase.com:5432/postgres?sslmode=require`  
   URL-encode `@` in password as `%40`.
5. Enable **pgvector** in SQL Editor:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
6. Run migrations (Render auto-runs on deploy; or locally):
   ```bash
   cd backend
   export DATABASE_URL="postgresql://postgres.<ref>:<password>@aws-*-*.pooler.supabase.com:5432/postgres?sslmode=require"
   export DATABASE_FALLBACK_ENABLED=false
   uv run python -m db.migrate
   ```

### B — Backend on Render (5 min)

1. [render.com](https://render.com) → sign up with GitHub.
2. **New → Blueprint** → select `FinSight_AI` repo.
3. When prompted, set these **secret** env vars:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Supabase pooler URL |
| `SUPABASE_URL` | `https://xxxx.supabase.co` |
| `CORS_ORIGINS` | `https://YOUR-PROJECT.vercel.app` (set after Vercel — redeploy once) |
| `BETA_ALLOWED_EMAILS` | `your@gmail.com` |
| `ANTHROPIC_API_KEY` | optional paid — for cloud chat only |

4. Wait for deploy → copy URL, e.g. `https://finsight-api.onrender.com`
5. Test: `curl https://finsight-api.onrender.com/health`

**Note:** Free tier cold-starts take **30–50 seconds** after idle.

### C — Frontend on Vercel (5 min)

1. [vercel.com](https://vercel.com) → sign up with GitHub.
2. **Add New → Project** → import `FinSight_AI`.
3. **Root Directory:** `frontend`
4. Environment variables:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Render URL from step B |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

5. **Deploy** → copy URL, e.g. `https://finsight-ai.vercel.app`

### D — Wire auth + CORS (3 min)

1. **Render** → `finsight-api` → Environment → set `CORS_ORIGINS` to your Vercel URL → **Manual Deploy**
2. **Supabase** → Authentication → URL Configuration:
   - **Site URL:** `https://your-project.vercel.app`
   - **Redirect URLs:** `https://your-project.vercel.app/**`, `http://localhost:3000/**`, `http://127.0.0.1:3000/**`  
     (must include `/**` wildcard — `/auth/callback` will not match without it)
3. Optional: edit `docs/config.js` with your Vercel URL for the GitHub Pages **Open FinSight** button.

### E — Verify

1. Open `https://your-project.vercel.app`
2. Sign in with Google
3. Dashboard loads
4. First API call after idle may be slow (Render waking up)

---

## Environment variable cheat sheet

### Render (`finsight-api`)

```
ENVIRONMENT=production
REQUIRE_AUTH=true
DATABASE_FALLBACK_ENABLED=false
DATABASE_URL=<supabase pooler>
SUPABASE_URL=https://<ref>.supabase.co
CORS_ORIGINS=https://<project>.vercel.app
BETA_ALLOWED_EMAILS=you@gmail.com
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
ANTHROPIC_API_KEY=        # optional paid — enables cloud chat (not free)
```

### Vercel (`frontend`)

```
NEXT_PUBLIC_API_URL=https://finsight-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| CORS error in browser | Add Vercel URL to Render `CORS_ORIGINS`, redeploy backend |
| Google login redirect error | Add Vercel URL to Supabase redirect URLs |
| `Could not load your data` | Run `alembic upgrade head` on production DB |
| 30–50s first load | Render free tier waking up — normal |
| Chat empty / errors (deployed) | Expected without `ANTHROPIC_API_KEY` — Ollama is local-only; chat **history** still syncs via Supabase |
| Chat history not shared local↔cloud | Use hotspot if campus Wi-Fi blocks Supabase; both must reach same Supabase DB |
| Local `Failed to fetch` | Use `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` not `localhost` |
| 403 on login | Add your email to `BETA_ALLOWED_EMAILS` |

---

## What stays local-only

| Feature | Free cloud | Local (`npm run dev`) |
|---------|------------|------------------------|
| Login + dashboard | Yes | Yes |
| Transactions / CSV | Yes | Yes |
| Budgets / alerts | Yes | Yes |
| Chat (Ollama) | No (history syncs) | Yes |
| Chat (Anthropic) | Yes (paid API) | Yes |

---

## Upgrade path (when you outgrow free)

| Need | Move to |
|------|---------|
| No cold starts | Render $7/mo or Railway $5/mo |
| More DB space | Supabase Pro |
| Custom domain | Vercel + DNS |

See also: [infra/railway/DEPLOY.md](./railway/DEPLOY.md) · [infra/DEPLOY-FROM-GITHUB.md](./DEPLOY-FROM-GITHUB.md)
