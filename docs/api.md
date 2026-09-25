# FinSight AI — API (overview)

Full route tables live in the OpenAPI schema at `GET /docs` when the API is running.

## Auth

All user routes expect `Authorization: Bearer <supabase_jwt>` when `REQUIRE_AUTH=true`.

| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/sync` | Upsert local user; demo provision if empty |
| GET | `/auth/me` | Profile |
| GET | `/auth/me/export` | PIPEDA access — full data export |
| DELETE | `/auth/me` | Account deletion |

## Core

Accounts, transactions, search, budgets, notifications, goals, insights — unchanged from v1.5.

## Chat

| Method | Path | Notes |
|--------|------|-------|
| POST | `/chat` | SSE stream; citations + evidence in `done` event |
| GET | `/chat/sessions` | History |
| GET | `/chat/sessions/{id}` | Session detail (includes evidence when present) |

## v2.0 additions

| Method | Path | Notes |
|--------|------|-------|
| GET | `/leaks` | Money-leak findings |
| PATCH | `/leaks/{id}` | dismiss / resolve |
| POST | `/leaks/{id}/draft` | Cancellation / dispute / fee-reversal draft |
| GET | `/planner/*` | Registered accounts, OSAP, what-if |
| GET | `/forecast` | Monte Carlo bands |
| GET | `/evals` | Admin/demo eval run history |
| GET | `/audit` | User-visible audit log |
| GET | `/health` | Liveness |
| GET | `/health/db` | DB connectivity |
| GET | `/capabilities` | Feature flags |

Amounts in agent replies use evidence tags: `[[$412.30|ev_17]]`.

## Frontend OpenAPI contract (optional)

TypeScript types for the API can be regenerated from the live OpenAPI schema
with [openapi-typescript](https://github.com/openapi-ts/openapi-typescript) —
full codegen is not required for v2.0.

```bash
# API must be running locally
cd frontend
npx openapi-typescript http://127.0.0.1:8000/openapi.json -o lib/api-types.d.ts
```

Prefer hand-maintained `lib/types.ts` for day-to-day work; refresh the generated
`.d.ts` when routes or response shapes change materially.
