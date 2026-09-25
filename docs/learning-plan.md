# FinSight AI — Complete Learning Plan

> Goal: Own every layer of this repo so you can explain it in an interview **without** reading from AI-generated notes. Built with AI is fine; *only* AI understands it is not.

**Related:** [Interview pitch](./interview-prep.md) · [Architecture](./architecture.md) · [ADRs](./adr/) · [Evals](./evals.md) · [Security](./security.md)

---

## How to use this plan

Do **not** binge-read docs. For each module:

| Step | What you do | Done when |
|------|-------------|-----------|
| 1. Map | Skim the listed files top-to-bottom (functions/classes only) | You can draw the module on paper |
| 2. Trace | Pick one real user action; follow request → DB → response in code | You can narrate the path without opening files |
| 3. Break | Change one line (or ask “what if X fails?”) and predict behavior | Prediction matches reality |
| 4. Explain | Say the 60s answer out loud (phone voice memo) | No filler, no “the AI wrote…” |
| 5. Drill | Answer the interview Qs at the end of the phase | Cold, no notes |

**Time budget (fits your system):** Weekdays 30–45 min = one micro-module. Weekend 1.5–3 hrs = one full phase + whiteboard.

**Order is non-negotiable.** Later phases assume you can already pitch trust + architecture.

---

## System map (memorize this first — Day 0)

```
Browser (Next.js)
  └─ Supabase Auth (JWT)
       └─ FastAPI (routers → services)
            ├─ Deterministic engines: leaks / planning / calculate / insights
            ├─ Agent: LangGraph ReAct → tools → evidence tags → numeric guardrail
            ├─ RAG: Voyage embed → pgvector + keyword → RRF → optional rerank
            └─ Postgres (Supabase) + RLS (defense-in-depth; app still scopes by user_id)
```

**Pitch line you must own:**

> Deterministic Python does the math. The LLM only picks tools and explains. Every dollar is evidence-tagged and guardrail-checked — or stripped.

**Stack one-liner:** FastAPI · LangGraph · Postgres/pgvector · Next.js · Supabase Auth · Groq · Voyage · Railway.

---

## Phase 0 — Product & interview framing (1–2 sessions)

**Why first:** Interviewers open with “tell me about a project.” If this is weak, deep code knowledge never gets heard.

| Learn | Source |
|-------|--------|
| Problem, pitch, 5-min deep dive | [interview-prep.md](./interview-prep.md) |
| C4 context + chat data flow | [architecture.md](./architecture.md) |
| Live metrics / version | [metrics.json](./metrics.json) |
| Freeze / what ships as v2 | [freeze.md](./freeze.md) |

**Practice**

1. Record a 60-second pitch. Cut anything that isn’t problem → trust mechanism → stack.
2. Record a 5-minute walkthrough using the 8 bullets in interview-prep (problem → architecture → ingest → retrieval → Canadian planning → security → evals → tradeoffs).
3. Write 3 resume bullets using real numbers from `metrics.json` (no placeholders).

**Exit checkpoint**

- [ ] You can answer “Why shouldn’t the LLM do the math?” in ≤20 seconds.
- [ ] You can name the evidence tag format: `[[$412.30|ev_17]]`.
- [ ] You know Groq 8B is default *because of free-tier rate limits*, not because it’s “smarter.”

---

## Phase 1 — Repo layout & local mental model (1 session)

| Path | Own this |
|------|----------|
| `README.md`, `DEV.md`, `DOCUMENTATION.md` | How prod vs local works |
| `backend/app/` | HTTP edge: routers, auth, middleware, DI |
| `backend/agent/` | LangGraph agent, tools, guardrails, privacy |
| `backend/rag/` | Embed, retrieve, cache, rerank |
| `backend/db/` | SQLAlchemy models, session |
| `backend/leaks/`, `backend/planning/`, `backend/insights/` | Deterministic money engines |
| `backend/ingest/`, `backend/integrations/` | CSV/PDF/Plaid into DB |
| `backend/evals/` | Golden sets + runner |
| `frontend/app/`, `frontend/lib/`, `frontend/components/` | Pages, API client, chat/evidence UI |
| `infra/`, `docs/adr/` | Deploy + *why* decisions |

**Drill:** From memory, list which folder owns: JWT verify, RRF fusion, FX leak vs BoC, TFSA rules YAML, SSE chat, evidence drawer.

**Exit checkpoint**

- [ ] You can sketch the monorepo tree and say what *not* to put in the frontend (secrets, service-role keys, money math).

---

## Phase 2 — Data model & migrations (2–3 sessions)

**Files**

- `backend/db/models.py` — `User`, `Account`, `Transaction`, `TransactionEmbedding` (`EMBEDDING_DIM = 1024`), chat, leaks, budgets, Plaid, audit, evals
- `backend/alembic/versions/` — history summarized in [architecture.md](./architecture.md)
- `backend/app/scoping.py` — app-level `user_id` / account scoping
- `infra/rls/policies.sql` — RLS (`auth.uid()` → `users.auth_id`)

**Concepts to master**

1. Negative amounts = debits; categories/merchants on transactions.
2. One embedding row per transaction (ADR 0003).
3. Dimension migrations: 768 (Ollama era) → **1024** (Voyage).
4. FastAPI DB role **bypasses** RLS → app scoping is still mandatory (ADR 0007).
5. Chat evidence lives in session JSON (`messages_json` / evidence payloads).

**Trace exercise**

Upload / seed a transaction → confirm row in `transactions` → embedding row → user-scoped query cannot see another user’s accounts.

**Interview Qs**

| Q | Must-say |
|---|----------|
| Why pgvector not Pinecone? | Same DB, RLS, no sync lag, cost/residency — ADR 0001 |
| Does RLS mean you’re safe without `user_id` filters? | No — API uses privileged role; RLS is defense-in-depth for PostgREST |
| Why 1024 dims? | Voyage `voyage-4-large`; Ollama 768 is optional offline fallback only |

**Exit checkpoint**

- [ ] Whiteboard: User → Accounts → Transactions → Embedding (+ ChatSession, LeakFinding).
- [ ] Explain one migration that resized vectors and why re-embed was required.

---

## Phase 3 — Auth, tenancy, API surface (2–3 sessions)

**Backend**

- `backend/app/auth.py` — JWT verify (JWKS ES256/RS256 or legacy HS256), beta allowlist, user sync
- `backend/app/routers/auth.py` — `/auth/sync`, `/auth/me`, export, delete (PIPEDA)
- `backend/app/dependencies.py`, `backend/app/main.py` — DI, router mount, middleware stack
- Middleware: `request_id`, `security_headers`, `chat_rate_limit`, `api_key`

**Frontend**

- `frontend/middleware.ts` + `frontend/lib/supabase/*` — session refresh
- `frontend/app/login/page.tsx`, `frontend/app/auth/callback/route.ts`
- `frontend/lib/api.ts`, `frontend/hooks/useAuthReady.ts` — Bearer token to API
- `frontend/next.config.mjs` — `/backend` proxy (middleware skips it)

**Trace exercise (critical)**

Google sign-in → Supabase session → frontend attaches `Authorization: Bearer` → FastAPI validates JWT → upserts `users.auth_id` → demo provision if empty → dashboard loads scoped data.

**Interview Qs**

| Q | Must-say |
|---|----------|
| Where is the source of truth for identity? | Supabase Auth; local `users` row is the app profile |
| How do you prevent IDOR? | Every query scoped by `user_id` / account_ids; never trust client-supplied user ids |
| PIPEDA access / deletion? | `GET /auth/me/export`, `DELETE /auth/me` |

**Exit checkpoint**

- [ ] Draw auth sequence with 5 boxes: Browser, Next middleware, Supabase, FastAPI auth, Postgres.
- [ ] Name two security headers and why CSP matters for an AI chat UI.

---

## Phase 4 — Deterministic engines (the product moat) (3–4 sessions)

This is what makes FinSight *not* “ChatGPT over a CSV.”

### 4a — Money leaks

| File | Responsibility |
|------|----------------|
| `backend/leaks/service.py` | Orchestrate detectors, persist `LeakFinding` |
| `backend/leaks/fx.py` + `boc.py` | FX markup vs Bank of Canada Valet |
| `backend/leaks/duplicates.py` | Duplicate charges |
| `backend/leaks/subscriptions.py` | Forgotten subs + price creep |
| `backend/leaks/fees.py` | Bank fees |
| `backend/leaks/drafts.py` | Cancellation / dispute letter drafts |
| `backend/app/routers/leaks.py` | REST + dismiss/resolve |

### 4b — Canadian planning & forecast

| File | Responsibility |
|------|----------------|
| `backend/planning/rules/2025.yaml`, `2026.yaml` | Versioned TFSA/RRSP/FHSA (etc.) rules |
| `backend/planning/registered.py`, `osap.py`, `student_tax.py` | Registered accounts, OSAP, student tax helper |
| `backend/planning/forecast.py` | Monte Carlo bands (seedable) — ADR 0008 |
| `backend/planning/scenarios.py` | What-if |
| `backend/app/routers/planner.py` | HTTP surface |

### 4c — Insights (dashboard math)

- `backend/insights/*` — recurring, anomalies, runway, TFSA helper, credit optimizer, reconcile
- `backend/app/routers/insights.py`, `dashboard.py`

**Practice**

1. Pick one leak type. Manually compute expected CAD on a sample of txs, then compare to detector output.
2. Open `rules/2026.yaml` and explain one contribution limit rule without paraphrasing vaguely.
3. Explain why Monte Carlo is Python with a seed, not “ask the LLM for a projection.”

**Interview Qs**

| Q | Must-say |
|---|----------|
| How do you know FX markup? | Compare charged rate / spread to BoC mid; engines emit amount + evidence |
| Why YAML rules? | Auditable, year-versioned, no prompt drift |
| What’s fingerprint on a leak? | Idempotent finding identity so rescans don’t spam duplicates |

**Exit checkpoint**

- [ ] Name all leak detector categories from memory.
- [ ] Say the ADR 0004 line: engines compute; LLM explains.

---

## Phase 5 — Ingest & integrations (2–3 sessions)

| File | Own this |
|------|----------|
| `backend/ingest/bank_csv.py` | CSV parse / normalize |
| `backend/ingest/merchants.py`, `dedupe.py`, `categorizer.py` | Merchant norm, dedupe, TF-IDF/rules categorizer |
| `backend/ingest/pdf/*` | PDF detect → extract → reconcile |
| `backend/ingest/jobs.py` | Async ingest jobs |
| `backend/integrations/plaid_*.py`, `token_crypto.py` | Link, sync, encrypt access tokens |
| `docs/categorizer.md` | Why keyword/TF-IDF over LLM zero-shot for cost |

**Trace exercise**

CSV upload → sanitize → categorize → insert txs → enqueue embeddings → searchable in RAG.

**Interview Qs**

- Why not LLM-categorize every transaction?
- How do you avoid double-importing the same bank row?
- How are Plaid tokens stored? (encrypted at rest — never logged)

**Exit checkpoint**

- [ ] End-to-end ingest story in under 90 seconds.

---

## Phase 6 — RAG / search (2–3 sessions)

**Files:** `backend/rag/embedder.py`, `indexing.py`, `retriever.py`, `filters.py`, `rerank.py`, `cache.py`  
**ADRs:** 0001, 0003, 0006 · **Docs:** [evals.md](./evals.md) ablation table

**Master this algorithm**

1. Parse structured filters (date/amount) → SQL `WHERE`.
2. Vector search (cosine on pgvector / HNSW).
3. Keyword path (tsvector if present, else ILIKE ranking).
4. Fuse rankings with **RRF** (`k=60`): `score(d) = Σ 1/(k + rank_i(d))`.
5. Optional rerank top N → top K.
6. Semantic cache keyed per user when safe.

**Practice**

- Implement RRF on paper with two ranked lists of 5 IDs.
- Explain why pure vector fails on “Starbucks $4.55 last Tuesday.”

**Interview Qs**

| Q | Must-say |
|---|----------|
| Hybrid why? | Exact merchant/amount + semantic “coffee habit” |
| One embedding per tx? | Simpler indexing, natural filter join — ADR 0003 |
| How do you measure retrieval? | recall@k, MRR, nDCG on `evals/retrieval.jsonl` |

**Exit checkpoint**

- [ ] Whiteboard RRF; state what `k=60` does (dampens top-heavy ranks).

---

## Phase 7 — Agent core (highest interview weight) (4–5 sessions)

This is the heart. Slow down.

### 7a — Graph & runner

| File | Role |
|------|------|
| `backend/agent/state.py` | TypedDict agent state |
| `backend/agent/graph.py` | LangGraph ReAct: model ↔ tools, `MAX_TOOL_LOOPS = 6`, arg validation |
| `backend/agent/runner.py` | Session load/save, profile, invoke graph, **numeric guardrail**, evidence list |
| `backend/agent/llm.py`, `routing.py`, `prompts.py` | Provider fallback, 8B/70B routing (ADR 0005), system prompts |
| `backend/agent/memory.py`, `user_profile.py`, `goals.py`, `scope.py` | History, learned profile, goals, account scope |

### 7b — Tools

| File | Role |
|------|------|
| `backend/agent/tools/__init__.py` | Tool registry / `execute_tool` |
| `aggregator.py`, `summarize.py`, `dates.py` | SQL aggregates / summaries |
| `calculate.py` | AST-whitelisted arithmetic only |
| `web_search.py` | Controlled external lookup |
| `backend/mcp/*` | Market / BoC / currency MCP-style tools |

### 7c — Trust layer

| File | Role |
|------|------|
| `guardrails/evidence.py` | `EvidenceStore`, `evidence_id`, attach to tool JSON |
| `guardrails/numeric.py` | Verify `$` / `%` against tool outputs; strip unverified |
| `privacy/redact.py` | PII scrub before LLM |
| `privacy/injection.py` | Delimit tool data; strip injection patterns |

### 7d — HTTP + UI

| File | Role |
|------|------|
| `backend/app/routers/chat.py` | SSE stream, status events, done + citations/evidence |
| `frontend/lib/chat-stream-manager.ts` | Client stream handling |
| `frontend/lib/evidence.ts` + `EvidenceDrawer.tsx` | Parse tags → clickable chips → drawer |
| `frontend/components/chat/formatAgentText.tsx` | Render tagged amounts |

**Trace exercise (memorize cold)**

```
User message
 → JWT + user scope
 → LangGraph: LLM selects tools (≤6 loops)
 → Each tool result gets evidence_id
 → Draft answer with [[$X|ev_N]]
 → verify_numeric_grounding; strip or regenerate path
 → Persist session + evidence
 → SSE to UI → chips → EvidenceDrawer
```

**Interview Qs (expect deep follow-ups)**

| Q | Must-say |
|---|----------|
| Why LangGraph? | Explicit ReAct, tool cap, observable steps — ADR 0002 |
| What if the model invents $50? | Guardrail fails; amount stripped / not shown as verified |
| Why `calculate` tool? | LLM must not free-form arithmetic; safe expression eval |
| Privacy mode? | Forces Ollama; keeps chat off cloud LLM |
| Fallback chain? | Groq → Claude → Ollama (`resolve_llm_fallback`) |

**Exit checkpoint**

- [ ] Narrate the chat path in under 2 minutes with file names.
- [ ] Open `numeric.py` and explain how an amount is considered “verified.”
- [ ] Explain tool-loop cap as a DoS / runaway-cost control.

---

## Phase 8 — Frontend product surfaces (2 sessions)

You don’t need every CSS class. You need **user journeys**.

| Journey | Pages / components |
|---------|-------------------|
| Dashboard KPIs | `app/page.tsx`, `InsightsPanels`, `KpiCard` |
| Chat + history | `app/chat`, `ChatHistorySidebar`, stream manager |
| Leaks | `app/leaks` |
| Planner / forecast | `app/planner`, `app/forecast` |
| Accounts / txs / search | `app/accounts`, `transactions`, `search` |
| Settings / privacy / notifications | settings, privacy, notifications, `BankConnectPanel` |

**Practice:** For each journey, name the API route(s) in [api.md](./api.md) and whether numbers come from engines or the agent.

**Exit checkpoint**

- [ ] Demo the live app while narrating backend calls (no silent clicking).

---

## Phase 9 — Evals, quality, CI (2 sessions)

| Artifact | Why it matters in interviews |
|----------|------------------------------|
| `backend/evals/golden.jsonl` | Grounded Q→SQL answers |
| `backend/evals/retrieval.jsonl` | Retrieval quality |
| `backend/evals/smoke.jsonl` | CI gate subset |
| `uv run python -m evals.run` | Persists `eval_runs` |
| [evals.md](./evals.md) | Hallucination rate, tool accuracy, recall |
| `.github/workflows/` | pytest, evals smoke, security audits |

**Must-say metrics language**

- Hallucinated-number rate = `$` in answer absent from tool outputs.
- Dry-run = fixtures without LLM (sanity of harness).
- CI fails if smoke accuracy drops >3 pts from baseline.

**Exit checkpoint**

- [ ] Answer “How do you know it works?” with harness + 3 metric names, not vibes.

---

## Phase 10 — Security, cost, deploy (2 sessions)

| Topic | Source |
|-------|--------|
| STRIDE + PIPEDA | [security.md](./security.md) |
| Cost / model choice | [cost.md](./cost.md), ADR 0005 |
| Railway + env matrix | [deploy.md](./deploy.md), `infra/RAILWAY-CHECKLIST.md`, `DEV.md` |
| CSV formula injection | `app/csv_sanitize.py` on export |

**Interview Qs**

- Threat you care about most for a finance agent? (hallucinated money, prompt injection via merchants, cross-user data leak)
- What ships where on `git push`? (frontend vs API vs migrations table in DEV.md)

**Exit checkpoint**

- [ ] STRIDE one row for “Transactions” from memory.
- [ ] Explain privacy mode vs “we encrypt the database.”

---

## Phase 11 — ADRs as interview ammo (1–2 sessions)

Read each ADR and write a **4-line card** (Context / Decision / Alternative rejected / Tradeoff):

| ADR | Topic |
|-----|-------|
| 0001 | pgvector vs Pinecone |
| 0002 | LangGraph vs ad-hoc loop |
| 0003 | One embedding per transaction |
| 0004 | Deterministic engines + LLM explainer |
| 0005 | Model routing 8B / 70B |
| 0006 | Hybrid search + rerank |
| 0007 | RLS + app scoping |
| 0008 | Monte Carlo forecast |

**Exit checkpoint**

- [ ] For any ADR number, give decision + one rejected alternative in ≤30 seconds.

---

## Suggested calendar (~3–4 weeks)

Aligned to weekday 30–45 min + one weekend deep session.

| Week | Focus |
|------|--------|
| **Week 1** | Phase 0–3 (pitch, layout, schema, auth). Weekend: whiteboard auth + ERD. |
| **Week 2** | Phase 4–5 (engines + ingest). Weekend: leak detector deep dive + manual calc. |
| **Week 3** | Phase 6–7 (RAG + agent). Weekend: full chat path on paper + voice memo. |
| **Week 4** | Phase 8–11 (UI journeys, evals, security, ADRs). Weekend: mock interview (below). |

If time-crunched before an interview: **0 → 7 → 4 → 6 → 9 → 10** (pitch, agent trust, engines, RAG, evals, security). Skip UI polish details.

---

## Mock interview script (90 minutes)

Do this once with a friend or voice memos. No notes.

1. **60s pitch**
2. **“Walk me through architecture”** (5 min, C4)
3. **“Follow a chat message through the system”** (8 min)
4. **“Show me where money is computed”** (leaks or TFSA)
5. **“How do you stop hallucinated dollars?”**
6. **“How does search work?”** (RRF)
7. **“How do you auth and isolate tenants?”**
8. **“How do you know quality?”** (evals)
9. **Tradeoff grill:** Why not LangChain agents alone? Why not Pinecone? Why not 70B always?
10. **Failure modes:** Voyage down, Groq rate limit, empty demo user, tool loop spinning, bad CSV

**Pass bar:** You pause to think, but you never say “I’d have to check what the AI generated.” Pointing to a file name is fine; reading the file mid-answer is not.

---

## Mastery checklist (print this)

### Product

- [ ] 60s pitch cold
- [ ] 5-min deep dive cold
- [ ] 3 resume bullets with real metrics

### Architecture

- [ ] C4 context from memory
- [ ] Separation: engines / LLM / guardrail
- [ ] All 8 ADRs as flashcards

### Data & auth

- [ ] ERD whiteboard
- [ ] JWT → user sync → scoping story
- [ ] RLS vs app scoping distinction

### Engines

- [ ] Leak types + BoC FX story
- [ ] Rules YAML year versioning
- [ ] Monte Carlo = deterministic + seedable

### Agent & RAG

- [ ] ReAct loop + tool cap
- [ ] Evidence tags + numeric guardrail
- [ ] Hybrid + RRF
- [ ] Embedding dim + provider fallback

### Proof & ops

- [ ] Eval metrics vocabulary
- [ ] PIPEDA export/delete
- [ ] Railway deploy matrix
- [ ] Live demo narration

---

## Anti-patterns (how AI-built projects fail interviews)

1. **Narrative without file anchors** — “We use LangGraph” with no `graph.py` / loop cap story.
2. **Confusing providers** — claiming Ollama is required in prod (it is optional offline).
3. **Trust theater** — saying “the model is careful” instead of guardrail + evidence.
4. **RLS cargo cult** — implying RLS alone secures the FastAPI path.
5. **Metric handwaving** — “evals look good” without hallucination rate / recall@k.
6. **Frontend-only fluency** — pretty UI, blank on `runner.py`.

---

## Daily micro-drill (10 minutes)

Pick one:

- Explain evidence tags to an imaginary non-engineer roommate.
- Draw RRF for 30 seconds.
- Name the fallback LLM chain.
- Trace `/leaks` from router → `scan_all_leaks` → one detector.
- Open `docs/metrics.json` and memorize the current headline numbers.

---

## After you finish this plan

1. Update [interview-prep.md](./interview-prep.md) resume bullets with measured numbers.
2. Do the [e2e-checklist.md](./e2e-checklist.md) on production while narrating.
3. Schedule a real mock interview; fix only the phases you stumbled on — don’t restart from Phase 0.
