# ADR 0007: RLS + app scoping

## Status

Accepted

## Context

App-level `account_ids_for_user` is necessary but not sufficient for fintech trust.

## Decision

Keep FastAPI scoping and add Supabase/Postgres Row-Level Security as defense-in-depth. Tests prove user A cannot read user B even with crafted requests.

## Consequences

- Dual enforcement; migrations must include policies
- Service role used only server-side
