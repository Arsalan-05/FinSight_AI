#!/usr/bin/env bash
# Apply Alembic migrations to Supabase Postgres (or any remote DATABASE_URL).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/backend"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: Set DATABASE_URL to your Supabase session pooler connection string first."
  echo "  Supabase → Connect → Session pooler (port 5432)"
  exit 1
fi

# Never migrate the local fallback when Supabase is unreachable from this machine.
export DATABASE_FALLBACK_ENABLED=false

echo "Running Alembic migrations against: ${DATABASE_URL%%@*}@***"
uv run python -m db.migrate
echo "Done. Tables: users, accounts, transactions, chat_sessions, transaction_embeddings"
