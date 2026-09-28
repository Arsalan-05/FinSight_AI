# Evaluation harness

Current numbers live in [`metrics.json`](./metrics.json); regenerate them with
`backend/.venv/bin/python scripts/generate_metrics.py`.

## What it answers

"How do you know the numbers are right?" Every question in the eval set has a
ground-truth answer computed directly from a frozen fixture, and every dollar
amount in an answer is scored by the same numeric guardrail that runs in
production (`agent/guardrails/numeric.py`).

## Artifacts

| Path | Purpose |
|------|---------|
| `backend/evals/fixtures/seed_persona.py` | Deterministic student persona: 600 transactions, 47 planted money leaks |
| `backend/evals/golden.jsonl` | 165 questions: aggregation, lookup, date reasoning, multi-step, insights, refusal, adversarial |
| `backend/evals/smoke.jsonl` | 30-question subset used by CI |
| `backend/evals/retrieval.jsonl` | 60 search queries with the relevant transaction ids |
| `backend/evals/run.py` | Runner; writes `evals/results/<timestamp>-<subset>.json` |
| `GET /evals` | Lists result files; the Docker build runs both subsets so production shows the scores of the deployed build |

## Metrics

| Metric | Definition |
|--------|------------|
| Answer accuracy | Numeric answer within tolerance of the SQL ground truth |
| Tool selection | Exact and partial match against the expected tools |
| Hallucinated-number rate | Share of `$` amounts the production guardrail rejects |
| Refusal accuracy | Off-topic and prompt-injection cases refused |
| Retrieval | recall@5 and nDCG@10 over `retrieval.jsonl` |

## Gate

`python -m evals.run` exits non-zero when a run falls below these floors, which
fails both CI and the Docker build:

| Metric | Floor |
|--------|-------|
| Answer accuracy | ≥ 0.97 |
| Tool selection (exact) | ≥ 0.97 |
| Refusal accuracy | 1.00 |
| Hallucinated-number rate | 0.00 |

```bash
cd backend
uv run python -m evals.run --subset smoke --dry-run   # CI
uv run python -m evals.run --subset full --dry-run    # all 165 questions
```

## Scope

The runner scores deterministic reference answers, so it checks the data layer,
tool contracts, retrieval ranking and the guardrail without spending API credits.
It does not grade live model prose. In production the same guardrail runs on
every reply and strips any amount a model produces that the tools cannot back up,
and `backend/scripts/check_e2e.py` smoke-tests the API, database and chat stream
against a configured environment.

Search ranking uses Postgres full-text and pgvector fused with reciprocal rank
fusion (k = 60), with date and amount filters applied in SQL before ranking
([ADR 0006](./adr/0006-hybrid-search-rerank.md)).
