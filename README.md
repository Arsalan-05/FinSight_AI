# FinSight AI

Personal finance intelligence — transaction ingest, pgvector search, and a stateful advisor grounded in your data. Canadian bank CSV import, optional Plaid sync, budgets, and spending insights.

**Status:** v1.4.0 — **100% complete · locked · June 30, 2026**  
**Owner:** Arsalan Amir Ali (100%)

---

## Live production (deployed)

| Service | URL / role |
|---------|------------|
| **App (Vercel)** | `https://fin-sight-ai-sepia.vercel.app` |
| **API (Render)** | `https://finsight-api-byrl.onrender.com` |
| **Database + Auth** | Supabase (`zibzsxwceivnziplciuq`) |

Invite-only beta · Google sign-in · dashboard, transactions, analytics, and **shared chat history** across local and deployed when both use Supabase.

> **Advisor AI:** **Groq** (free) for all chat on Mac + Render. **Ollama** (free, local) for search embeddings only — Groq cannot do search vectors.

## Groq everywhere possible (free)

| Feature | Provider | Runs on |
|---------|----------|---------|
| Chat / advisor | **Groq** `llama-3.3-70b-versatile` | Groq cloud |
| Memory summaries | **Groq** | Groq cloud |
| Profile learning | **Groq** | Groq cloud |
| Semantic search | **Ollama** `nomic-embed-text` | Your Mac only |
| Dollar amounts | SQL tools | Your database |

Set `GROQ_API_KEY` in `.env` (Mac) and Render. Run `ollama pull nomic-embed-text` once on your Mac for search.

Deploy guide: **[infra/DEPLOY-FREE.md](./infra/DEPLOY-FREE.md)** ($0 stack)

---

## Quick start (local)

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
# Add GROQ_API_KEY (free: console.groq.com) + Supabase keys

docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head

# Terminal 1 — backend (use 127.0.0.1 to avoid IPv6 localhost issues)
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000** → sign in with Google.

**Prerequisites:** Free [Groq](https://console.groq.com) API key, [Ollama](https://ollama.com) for embeddings (`ollama pull nomic-embed-text`), [uv](https://docs.astral.sh/uv/), Node 20+, Docker (optional Postgres fallback).

**Network tip:** Campus Wi-Fi often blocks Supabase. Use a **hotspot** for shared cloud data + chat history, or rely on local Postgres fallback (`DATABASE_FALLBACK_ENABLED=true`).

---

## Architecture at a glance

```
Local dev:   localhost:3000 → 127.0.0.1:8000 → Supabase (or Docker fallback) + Ollama
Production:  Vercel         → Render API      → Supabase (no Ollama)
```

| Feature | Local | Deployed |
|---------|-------|----------|
| Login (Google) | ✅ | ✅ |
| Dashboard / data | ✅ | ✅ |
| Chat history (Supabase) | ✅ (hotspot / reachable pooler) | ✅ |
| AI advisor replies | ✅ Groq (same as Render) | ✅ Groq (free API key) |

---

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Ollama · Vercel · Render

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
