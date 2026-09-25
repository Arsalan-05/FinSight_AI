# Evaluation harness

Numbers in this file must match [`metrics.json`](./metrics.json) after each baseline run.

## Goal

Answer "how do you know it works?" with SQL-grounded metrics. Every later phase is measured against this harness.

## Artifacts

| Path | Purpose |
|------|---------|
| `backend/evals/fixtures/` | Deterministic seeded demo persona (~600 txs) |
| `backend/evals/golden.jsonl` | 150 questions with ground-truth SQL |
| `backend/evals/retrieval.jsonl` | 60 queries with relevant transaction IDs |
| `backend/evals/smoke.jsonl` | 30-question CI subset |
| `uv run python -m evals.run` | Runner → `eval_runs` table |

## Metrics

| Metric | Definition |
|--------|------------|
| Answer accuracy | Numeric match within tolerance |
| Tool-selection accuracy | Exact and partial |
| Hallucinated-number rate | $ amounts in answer absent from tool outputs |
| Retrieval | recall@5, recall@10, MRR, nDCG@10 |
| Refusal accuracy | Out-of-scope questions |
| Injection resistance | Adversarial cases handled safely |
| Cost/latency | p50/p95, tokens, $ / 1k queries |

## Model comparison (baseline)

Run: `uv run python -m evals.run --model <id> --subset full`

| Model | Role in product | Answer acc. | Tool exact | Halluc. $ rate | Refusal | Injection |
|-------|-----------------|-------------|------------|----------------|---------|-----------|
| Dry-run (fixture) | — | 1.00 | 1.00 | 0.133 | 1.00 | — |
| Groq gpt-oss-20b | **basic** tier | — | — | — | — | — |
| Claude Sonnet (`claude-sonnet-4-6`) | **heavy** tier | — | — | — | — | — |
| Groq gpt-oss-120b | heavy fallback (no Anthropic key) | — | — | — | — | — |
| Ollama qwen2.5:7b | privacy / offline | — | — | — | — | — |

*Dry-run scores fixture ground-truth helpers without an LLM. Live model rows fill after `evals.run --subset full`. CI fails if smoke accuracy drops >3 pts from baseline.*

## Ablation (Phase 6)

Numbers pending measurement against `evals/retrieval.jsonl` after a full retrieval run.

| Step | recall@5 | nDCG@10 | Δ recall@5 |
|------|----------|---------|------------|
| Baseline vector | — (pending measurement) | — (pending measurement) | — |
| + hybrid (RRF) | — (pending measurement) | — (pending measurement) | — |
| + structured filters | — (pending measurement) | — (pending measurement) | — |
| + rerank | — (pending measurement) | — (pending measurement) | — |
| + embedding enrichment | — (pending measurement) | — (pending measurement) | — |

Hybrid path: when a Postgres `tsvector` column is missing, Python RRF fuses keyword ILIKE
ranking with vector cosine ranking (`rag.retriever.rrf_fuse`, k=60). Structured date/amount
filters apply as SQL `WHERE` before search. Rerank stub is a simple token-overlap boost
(Cohere interface ready in `rag.rerank`).

## LLM-as-judge

Used **only** for explanation quality (clarity + grounding, 1–5). Validated against 30 hand-labeled answers; report agreement rate here after calibration.
