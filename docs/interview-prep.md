# Interview prep — FinSight AI

## 60-second pitch

FinSight AI is a Canadian personal-finance agent that finds money you're losing — FX markups, duplicate charges, subscription creep, bank fees — and **proves every dollar** it shows. Deterministic Python engines do the math; the LLM only picks tools and explains. Evidence tags like `[[$412.30|ev_17]]` wire answers back to SQL/tool output, and a numeric guardrail rejects hallucinated amounts. Stack: FastAPI, LangGraph, Postgres/pgvector, Next.js, Groq + Claude (tiered), Voyage, Railway.

## 5-minute deep dive

1. **Problem** — ChatGPT-style finance bots invent numbers. Canadians also miss FX spreads and silent fee changes.
2. **Architecture** — Separation of concerns: engines (leaks, planning, calculate) → tool results with `evidence_id` → LLM draft with tags → guardrail → UI chips + drawer.
3. **Ingestion** — CSV/PDF + merchant normalization + reconcile; optional Plaid; async jobs.
4. **Retrieval** — One Voyage embedding per transaction, hybrid search + RRF, optional rerank, semantic cache.
5. **Canadian planning** — TFSA/RRSP/FHSA rules YAML, OSAP, student tax helper, Monte Carlo forecast (seedable).
6. **Trust & security** — RLS + app scoping, PII redaction, privacy mode (Ollama-only), audit log, PIPEDA export/delete.
7. **Evals** — Frozen ~600-tx persona, golden set, CI smoke dry-run gate, metrics (hallucination rate, tool selection, NDCG).
8. **Tradeoffs** — Tiered LLMs: Groq 8B for fast spend Q&A; Claude Sonnet for planning/advice (Groq 70B if no Anthropic key); pgvector over Pinecone for residency/cost; no LLM arithmetic.

## Resume bullet templates

Replace `[N]`, `[X%]`, `[Y]` with measured metrics from [`docs/metrics.json`](./metrics.json) / evals.

- Built an evidence-tagged finance agent (FastAPI + LangGraph + Next.js) where **every dollar amount** is tied to tool output and blocked by a numeric guardrail — `[X%]` hallucinated-number rate on the golden set.
- Shipped a money-leak engine (FX vs BoC Valet, duplicates, subscription creep, bank fees) with action drafts; planted-leak precision `[X%]` / recovered `[N]` CAD on the eval persona.
- Designed hybrid pgvector retrieval (Voyage 1024-d) with RRF + filters; retrieval recall@k `[X%]` / MRR `[Y]` on the 60-query set.
- Implemented Canadian planning engines (registered accounts, OSAP, student tax, Monte Carlo forecast) driven by versioned `rules/{year}.yaml` — zero LLM math.
- Owned Railway deploy, Alembic migrations, SSE chat, Supabase Auth, and a CI gate (`pytest` + evals smoke dry-run).

## Architecture talking points

| Question | Short answer |
|----------|--------------|
| Why not let the LLM calculate? | Non-deterministic; fails compliance/trust. AST-whitelisted `calculate` + engines only. |
| Why pgvector? | Same DB as transactions; RLS; no sync lag; cost. See ADR 0001. |
| Why LangGraph? | Explicit ReAct loop, tool cap, easier debugging than ad-hoc loops. ADR 0002. |
| Fallback LLM? | Heavy: Claude → Groq 70B; chain Groq → Claude → Ollama (`resolve_llm_fallback`). |
| Model routing? | `route_chat_tier` → basic Llama / heavy Claude (ADR 0005). |
| Demo offline? | `docker-compose.demo.yml` + optional host Ollama. |

## Links

- [Learning plan](./learning-plan.md) (phase-by-phase mastery) · [Architecture](./architecture.md) · [ADRs](./adr/) · [Evals](./evals.md) · [Security](./security.md) · [Freeze](./freeze.md)
