# Changelog

All notable changes to FinSight AI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-28

Final release. FinSight is feature-complete and in maintenance.
Updated 2026-11-15 with leak-detection fixes from the audit (`audit/`); the version stays 2.0.0.

### Added
- Evidence tags on every dollar amount, a numeric guardrail that strips anything the tools cannot back up, and a safe `calculate` tool
- Money-leak engine: FX markup (Bank of Canada rates), duplicate charges, bank fees, subscription creep, and drafted cancellation / dispute letters
- Canadian planning: TFSA / RRSP / FHSA contribution order, OSAP estimate, student tax helper, what-if scenarios, Monte Carlo forecast
- Hybrid transaction search (keyword + pgvector with reciprocal rank fusion), SQL-side filters, semantic cache
- Tiered chat: Groq `gpt-oss-20b` for lookups, Claude `claude-sonnet-4-6` for planning and coaching, Groq `gpt-oss-120b` fallback
- Concurrent chats with client-generated session ids, recovery after dropped streams, and Markdown replies (tables, headings, lists)
- Evidence drawer that explains each source in plain English
- Eval harness: 165-question golden set, 60 retrieval queries, frozen 600-transaction persona, and a gate that fails CI and the Docker build
- Category corrections stick: changing a transaction's category saves a rule for that merchant, recategorizes the rest of the user's history from it, and applies to future imports. `PATCH /transactions/{id}` returns `recategorized` and accepts `?learn=false`
- Row-level security policies, PII redaction before LLM calls, audit log, security headers, CSV formula sanitizing on export
- `scripts/seed_full.py` loads a year of realistic data into any account
- `as_of` scan date on `scan_all_leaks`, the FX, fee and forgotten-subscription detectors, and `detect_recurring_charges`; defaults to today, so behaviour is unchanged when omitted
- `seed` parameter on the eval persona builder and loader for robustness checks

### Changed
- Deployment moved to Railway (web and API) with a same-origin `/backend` proxy
- Backend on Python 3.11 with SQLAlchemy 2.1, psycopg 3 and LangGraph 1.x; frontend on Next.js 16.3
- Cash runway now divides cash on hand by the monthly shortfall and reports "cash-flow positive" when income covers spending
- Weekly questions use a true last-7-days window
- Groq rate limits fall through to Claude instead of stalling the reply
- Memory and profile learning run after the reply is sent
- Price-creep alerts only fire for subscription-like charges: at least three charges, weekly-to-monthly cadence, and a price that rarely changes. Variable spending (groceries, fuel, dining, utility bills) no longer produces "price increase" alerts
- Forgotten-subscription alerts skip rent/housing, transfers, savings and income
- Eval persona: USD purchases are priced at the Bank of Canada reference plus a 2–3% card markup, and the planted-leak list now holds only real leaks (45; rent and the prompt-injection row stay as test data)

### Fixed
- Search, goals, budgets and other collection routes no longer 404 behind the proxy
- Deleted chats no longer reappear, and deleting asks for confirmation
- Questions sent from the weekly brief are no longer dropped
- Safari "Load failed" on long replies
- Auth 500s with ES256 Supabase tokens
- Category edits now clear the chat retrieval cache, so the advisor sees new totals straight away

### Security
- `pip-audit` and `npm audit` clean at release; weekly scans in CI

## [1.5.1] - 2026-07-01

### Added
- Finance-only advisor scope, background and concurrent chat, unified alert toggles
- Follow-up context and learned profile updates
- Railway, Supabase, Groq and Voyage deployment stack

## [1.5.0] - 2026-07-01

### Added
- Canadian bank CSV ingest, Plaid sync, budgets, spending insights
- LangGraph ReAct agent with SQL and search tools
- pgvector semantic search with Voyage embeddings

[2.0.0]: https://github.com/Arsalan-05/FinSight_AI/compare/v1.5.1...v2.0.0
[1.5.1]: https://github.com/Arsalan-05/FinSight_AI/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Arsalan-05/FinSight_AI/releases/tag/v1.5.0
