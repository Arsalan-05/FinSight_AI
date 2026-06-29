#!/usr/bin/env bash
# Apply Alembic migrations to Supabase Postgres (or any remote DATABASE_URL).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/backend"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: Set DATABASE_URL to your Supabase connection string first."
  echo "  Project Settings → Database → Connection string (Session mode or Direct)"
  exit 1
fi

echo "Running Alembic migrations against: ${DATABASE_URL%%@*}@***"
uv run alembic upgrade head
echo "Done. Tables: users, accounts, transactions, chat_sessions, transaction_embeddings"
