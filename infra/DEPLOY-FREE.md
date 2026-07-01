# Deploy FinSight for $0 (Vercel + Render + Supabase)

One live app URL on **Vercel**. Backend on **Render free tier**. Database + auth on **Supabase free tier**.

| Service | Role | Cost |
|---------|------|------|
| [Vercel](https://vercel.com) | Next.js frontend | Free |
| [Render](https://render.com) | FastAPI backend | Free (sleeps after 15 min idle) |
| [Supabase](https://supabase.com) | Postgres + Google login | Free |
| [GitHub Pages](https://pages.github.com) | Optional landing page | Free |

**Your app URL:** `https://<project>.vercel.app` (one link for everything)

> **Free cloud AI:** **Groq** `llama-3.1-8b-instant` for chat (`GROQ_API_KEY`, `GROQ_MODEL`) and **Voyage** for search (`VOYAGE_API_KEY`, `voyage-4-large`, 200M free tokens total). Ollama is optional offline fallback only.

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
| `GROQ_API_KEY` | **free** — chat ([console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` (recommended free tier) |
| `VOYAGE_API_KEY` | **free** — semantic search ([dash.voyageai.com](https://dash.voyageai.com); add billing card for higher RPM, 200M tokens still free) |
| `ANTHROPIC_API_KEY` | optional paid — alternative cloud chat |

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
LLM_PROVIDER=groq
EMBEDDING_PROVIDER=voyage
GROQ_API_KEY=           # free at console.groq.com
GROQ_MODEL=llama-3.1-8b-instant
VOYAGE_API_KEY=         # free at dash.voyageai.com (200M tokens on voyage-4-large)
VOYAGE_MODEL=voyage-4-large
ANTHROPIC_API_KEY=      # optional paid alternative
```

### Vercel (`frontend`)

```
NEXT_PUBLIC_API_URL=https://finsight-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

---

## Deploy workflow (after `git push`)

| Service | Typical behavior |
|---------|------------------|
| **Vercel** (frontend) | **Auto-deploys** on push to `main` — no action needed |
| **Render** (backend) | **Manual deploy** if auto-deploy is off — Dashboard → service → Deploy |
| **Supabase** | No deploy — DB/auth unchanged unless you run migrations |

Only **Render** needs `GROQ_API_KEY`, `GROQ_MODEL`, and `VOYAGE_API_KEY`. Vercel only needs `NEXT_PUBLIC_*` vars.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| CORS error in browser | Add Vercel URL to Render `CORS_ORIGINS`, redeploy backend |
| Google login redirect error | Add Vercel URL to Supabase redirect URLs |
| `Could not load your data` | Run `alembic upgrade head` on production DB |
| 30–50s first load | Render free tier waking up — normal |
| Chat errors | Missing `GROQ_API_KEY` / `VOYAGE_API_KEY` on Render | Add keys → Manual Deploy |
| Groq HTTP 429 | Free-tier rate limit | Use `llama-3.1-8b-instant`; wait for auto-retry |
| Groq `tool_use_failed` | Old deploy | Pull latest `main` and redeploy Render |
| Voyage slow / billing message | No card on Voyage | Add card at dashboard.voyageai.com; rebuild search index on Search page |
| Search empty after deploy | Embeddings cleared by migration | Search → **Rebuild search index** (batched, may take time) |
| Chat history not shared local↔cloud | Campus Wi-Fi blocks Supabase | Use hotspot; or use production only |
| Local `Failed to fetch` | Use `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` not `localhost` |
| 403 on login | Add your email to `BETA_ALLOWED_EMAILS` |

---

## Production vs local

| | **Production** | **Local (optional)** |
|--|----------------|----------------------|
| Purpose | Daily use, demos, portfolio | Coding, tests, experiments |
| Login + dashboard | Yes | Yes |
| Advisor chat (Groq) | Yes | Yes (same API keys) |
| Semantic search (Voyage) | Yes | Yes (same API keys) |
| Required to use FinSight? | **Yes** | **No** |

Ollama is optional offline fallback when Groq/Voyage keys are unset locally.

---

## Upgrade path (when you outgrow free)

| Need | Move to |
|------|---------|
| No cold starts | Render $7/mo or Railway $5/mo |
| More DB space | Supabase Pro |
| Custom domain | Vercel + DNS |

See also: [infra/railway/DEPLOY.md](./railway/DEPLOY.md) · [infra/DEPLOY-FROM-GITHUB.md](./DEPLOY-FROM-GITHUB.md)
