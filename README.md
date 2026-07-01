# FinSight AI

Personal finance intelligence — transaction ingest, pgvector search, and a stateful advisor grounded in your data. Canadian bank CSV import, optional Plaid sync, budgets, and spending insights.

**Status:** v1.5.1 — **100% complete · locked · July 1, 2026**  
**Owner:** Arsalan Amir Ali (100%)

---

## Live production (deployed)

| Service | URL / role |
|---------|------------|
| **App (Vercel)** | `https://fin-sight-ai-sepia.vercel.app` |
| **API (Render)** | `https://finsight-api-byrl.onrender.com` |
| **Database + Auth** | Supabase (`zibzsxwceivnziplciuq`) |

Invite-only beta · Google sign-in · dashboard, transactions, analytics, and **shared chat history** on Supabase.

> **Use production for daily use.** Local is only for coding, testing, and debugging.

> **AI stack (free):** **Groq** `llama-3.1-8b-instant` for chat · **Voyage** `voyage-4-large` for semantic search. Ollama is optional offline fallback only.

## Free AI stack (Groq + Voyage)

| Feature | Provider | Runs on |
|---------|----------|---------|
| Chat / advisor | **Groq** `llama-3.1-8b-instant` | Groq cloud |
| Memory summaries | **Groq** | Groq cloud |
| Profile learning | **Groq** (`call_llm_plain` — no tools) | Groq cloud |
| Semantic search | **Voyage** `voyage-4-large` | Voyage cloud |
| Dollar amounts | SQL tools | Your database |

Set `GROQ_API_KEY`, `GROQ_MODEL=llama-3.1-8b-instant`, and `VOYAGE_API_KEY` in `.env` (Mac) and Render. Sign up free at [console.groq.com](https://console.groq.com) and [dash.voyageai.com](https://dash.voyageai.com).

Deploy guide: **[infra/DEPLOY-FREE.md](./infra/DEPLOY-FREE.md)** ($0 stack)

**v1.5.1 highlights:** Finance-only advisor scope · background/concurrent chat · unified alert toggles · follow-up context · reliable learned profile updates.

---

## Quick start (local — optional, for development only)

Only run this when **editing code** or **running tests**. For normal use, open the production URL above.

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
# Add GROQ_API_KEY + VOYAGE_API_KEY + Supabase keys

docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head

# Terminal 1 — backend
cd backend && set -a && source ../.env && set +a
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

**Prerequisites:** Free [Groq](https://console.groq.com) + [Voyage](https://dash.voyageai.com) API keys, [uv](https://docs.astral.sh/uv/), Node 20+, Docker (optional Postgres fallback).

**Network tip:** Campus Wi-Fi often blocks Supabase. Use a **hotspot** for shared cloud data + chat history, or rely on local Postgres fallback (`DATABASE_FALLBACK_ENABLED=true`).

---

## Architecture at a glance

```
Production (primary):  Vercel → Render API → Supabase + Groq + Voyage
Local (workshop):      localhost:3000 → 127.0.0.1:8000 → same stack when coding
```

| Feature | Production | Local (optional) |
|---------|------------|------------------|
| Login (Google) | ✅ | ✅ |
| Dashboard / data | ✅ | ✅ (hotspot for Supabase) |
| AI advisor | ✅ Groq | ✅ Groq (same keys) |
| Semantic search | ✅ Voyage | ✅ Voyage (same keys) |
| Purpose | **Daily use · demos** | **Code · test · debug** |

---

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Groq · Voyage · Vercel · Render

---

## Documentation

| Doc | Purpose |
|-----|---------|
| **[DOCUMENTATION.md](./DOCUMENTATION.md)** | Full technical reference |
| **[infra/DEPLOY-FREE.md](./infra/DEPLOY-FREE.md)** | Vercel + Render + Supabase ($0) |
| **[DEV.md](./DEV.md)** | Developer notes |
| **[infra/DEPLOY-FROM-GITHUB.md](./infra/DEPLOY-FROM-GITHUB.md)** | Railway alternative |

---

## License & ownership

Copyright (c) 2026 **Arsalan Amir Ali** — 100% owner. MIT License — see [LICENSE](./LICENSE) and [DOCUMENTATION.md §20](./DOCUMENTATION.md#20-rights-license--ownership).
