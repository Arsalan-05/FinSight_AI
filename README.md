# FinSight AI

AI personal finance agent that answers questions about your own spending and flags money leaks. Built end to end by me.

## What it does

- Answers questions about your spending using RAG over transaction history, LangGraph workflows and MCP-connected tools.
- Gives the agent 14 tools, with hybrid search over your transactions.
- Flags money leaks. On a synthetic user with 45 planted leaks it flags 39 of 45 when the scan is dated to the end of the fixture year, and a precision fix cut false alarms by about half.
- Runs on a 78-endpoint backend with 348 automated tests; CI runs on pushes and pull requests to main.

## Features

- **Grounded answers.** Each dollar figure in an advisor answer is tagged to the tool result it came from, and a numeric guardrail removes any amount the data cannot back up.
- **Money-leak detectors.** Flags FX markups (compared with Bank of Canada rates), duplicate charges, bank fees, subscription price creep and forgotten subscriptions, then drafts a cancellation or dispute letter.
- **Canadian planning.** A TFSA, RRSP and FHSA contribution optimizer, OSAP repayment scenarios, student tuition tax credit estimates and a Monte Carlo cash forecast.
- **Privacy.** Personal details are redacted before text goes to a third-party LLM, and the database uses Postgres row-level security.
- **Your data.** JSON export of your data, account deletion and an audit log.

## Stack

Python, FastAPI, LangGraph, PostgreSQL, pgvector, Next.js

## Getting started

Copy the example environment files:

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

In `.env`, add `GROQ_API_KEY`, `VOYAGE_API_KEY` and the Supabase settings (`SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`). `ANTHROPIC_API_KEY` is optional. `.env.example` lists every variable name. In `frontend/.env.local`, fill in the variables it lists (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SITE_URL`).

Start the database and the backend:

```bash
docker compose up -d db
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The frontend runs at http://localhost:3000.

## Tests

Backend, from `backend/`:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy app/ agent/ db/ rag/ insights/
uv run python -m evals.run --subset smoke --dry-run
```

Frontend, from `frontend/`:

```bash
npm run lint
npm run type-check
npm run build
```

CI runs all of these on every push and pull request to `main` (see `.github/workflows/ci.yml`).

## Status

Deployed; solo project.

## License

Copyright (c) 2026 Arsalan Amir Ali. Released under the [MIT License](./LICENSE).
