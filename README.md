# FinSight AI

**A Canadian finance agent that finds money you're losing, proves every number it shows, and never lets the LLM do the math.**

**Stable target:** v2.0.0 · metrics from [`docs/metrics.json`](./docs/metrics.json)  
**Owner:** Arsalan Amir Ali (100%) · [MIT License](./LICENSE)

| Live app | API |
|----------|-----|
| Railway frontend (custom domain TBD) | Railway API |

> Invite-only beta · Google sign-in · demo mode available.

---

## Stack

Python · FastAPI · LangGraph · PostgreSQL · pgvector · Next.js · Supabase Auth · Groq · Claude · Voyage · Railway

**AI:** Tiered chat — Groq Llama 8B (basic) + Claude Sonnet (heavy) · Voyage `voyage-4-large` (1024-d) for search · Ollama optional offline only.  
**LLM fallback:** Claude heavy → Groq 70B if no Anthropic key; overall chain Groq → Claude → Ollama (`resolve_llm_fallback`).

## Quick start (local)

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
# Add GROQ_API_KEY + ANTHROPIC_API_KEY (optional heavy) + VOYAGE_API_KEY + Supabase keys

docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

cd frontend && npm ci && npm run dev
```

Open http://localhost:3000

**Demo (API + DB only):** `docker compose -f docker-compose.demo.yml up --build` — seed command in that file's header.

## Architecture

Deterministic Python engines compute money. The LLM selects tools and explains. Every dollar amount is evidence-tagged and guardrail-checked.

See [`docs/architecture.md`](./docs/architecture.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [Architecture](./docs/architecture.md) | C4, data flow, migrations |
| [API](./docs/api.md) | Route overview + OpenAPI TS note |
| [Deploy](./docs/deploy.md) | Railway + Supabase |
| [Evals](./docs/evals.md) | Golden set, baselines, ablations |
| [Security](./docs/security.md) | STRIDE + PIPEDA |
| [Interview prep](./docs/interview-prep.md) | Pitch, deep dive, resume bullets |
| [Learning plan](./docs/learning-plan.md) | Phase-by-phase mastery for interviews |
| [E2E checklist](./docs/e2e-checklist.md) | 10 smoke flows |
| [Freeze](./docs/freeze.md) | v2.0.0 maintenance mode |
| [ADRs](./docs/adr/) | Architecture decisions (8) |
| [CONTRIBUTING](./CONTRIBUTING.md) | Conventional commits |
| [CHANGELOG](./CHANGELOG.md) | Keep a Changelog |
| [SECURITY](./SECURITY.md) | Vulnerability reporting |

## License

Copyright (c) 2026 Arsalan Amir Ali. MIT — see [LICENSE](./LICENSE).
