# v2.0 Master Plan — GitHub issues

Create a milestone named **v2.0** and open one issue per task below (or run when `gh` is available):

```bash
gh milestone create "v2.0" --description "FinSight AI provably excellent — then freeze"
# then for each line: gh issue create --title "..." --milestone "v2.0" --label v2
```

## Phase 0 — Foundation
- [ ] Fix license contradiction (MIT)
- [ ] Single source of truth docs/metrics.json
- [ ] Fix stale docs (1024-d, Ollama optional, no Vercel/Render)
- [ ] Custom domain → Railway
- [ ] Secret scan + key rotation
- [ ] Split DOCUMENTATION into /docs
- [ ] CHANGELOG, CONTRIBUTING, SECURITY, issue templates

## Phase 1 — Evaluation harness
- [ ] Frozen eval fixture (~600 txs)
- [ ] Golden set 150 questions
- [ ] Retrieval set 60 queries
- [ ] Runner + eval_runs table
- [ ] Metrics suite
- [ ] Model comparison matrix
- [ ] LLM-as-judge calibration
- [ ] CI smoke gate (30 Q)
- [ ] /evals dashboard

## Phase 2 — Trust layer
- [ ] Evidence IDs + [[$|ev]] chips + drawer
- [ ] Numeric guardrail
- [ ] calculate tool (no eval)
- [ ] Confidence / missing-data evals
- [ ] Model routing Llama basic / Claude heavy

## Phase 3 — Money-leak engine
- [ ] FX markup + BoC rates
- [ ] Duplicate charge detector
- [ ] Subscription price creep
- [ ] Bank fee scanner
- [ ] Forgotten subscriptions
- [ ] leak_findings + API
- [ ] Action drafts
- [ ] Money Recovered card
- [ ] Planted-leak evals ≥90% precision

## Phase 4 — Canadian planning
- [ ] rules/{year}.yaml
- [ ] Registered-account optimizer
- [ ] OSAP planner
- [ ] Student tax helper
- [ ] Monte Carlo forecast
- [ ] What-if scenarios
- [ ] Agent tools + disclaimers

## Phase 5 — Ingestion depth
- [ ] PDF parser + reconciliation
- [ ] Merchant normalization
- [ ] ML categorizer comparison
- [ ] Cross-source dedup
- [ ] Async ingestion worker

## Phase 6 — Retrieval & agent
- [ ] Hybrid search RRF
- [ ] Structured filters
- [ ] Reranker
- [ ] Embedding enrichment
- [ ] Tool arg validation + loop cap
- [ ] Semantic cache
- [ ] Ablation table

## Phase 7 — Security
- [ ] RLS + isolation tests
- [ ] PII redaction
- [ ] Privacy mode (Ollama only)
- [ ] Injection defense
- [ ] Audit log
- [ ] Headers, rate limits, upload sanitization
- [ ] Encryption docs
- [ ] Dependabot / pip-audit / CodeQL
- [ ] Threat model + PIPEDA doc

## Phase 8 — Infra
- [ ] Tracing (Langfuse/OTel)
- [ ] Sentry
- [ ] Structured JSON logs
- [ ] Health/SLOs + status page
- [ ] k6 load test
- [ ] DB indexes + pooling
- [ ] Staging → prod CI/CD
- [ ] Backups + restore test
- [ ] Cost dashboard

## Phase 9 — Frontend
- [ ] Public demo mode
- [ ] Guided tour
- [ ] /leaks /planner /forecast
- [ ] Evidence drawer
- [ ] a11y + Lighthouse ≥90
- [ ] PWA + mobile
- [ ] Empty/error/loading states
- [ ] FR strings for key pages

## Phase 10 — Testing
- [ ] Coverage targets
- [ ] Hypothesis property tests
- [ ] Frontend unit tests
- [ ] 10 Playwright E2E flows
- [ ] OpenAPI TS client contract
- [ ] Migration up/down tests
- [ ] Visual regression

## Phase 11 — Presentation
- [ ] README one-screen
- [ ] 8 ADRs
- [ ] Demo video + write-up
- [ ] Resume bullets + interview prep
- [ ] LinkedIn / portfolio

## Phase 12 — Freeze
- [ ] Pin locks + digests
- [ ] docker compose offline demo
- [ ] Recorded fallback assets
- [ ] Static snapshot (Pages)
- [ ] Model fallback chain
- [ ] Keep-alive Action
- [ ] Dependabot monthly
- [ ] Tag v2.0.0 + maintenance mode
