#!/usr/bin/env bash
# End-to-end Supabase setup: extensions → migrations → seed demo data
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Load .env from repo root
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PROJECT_REF="${SUPABASE_URL:-}"
PROJECT_REF="${PROJECT_REF#https://}"
PROJECT_REF="${PROJECT_REF%.supabase.co}"

# Use DATABASE_URL from .env if it points at Supabase; else build from password
if [[ "${DATABASE_URL:-}" == *"supabase"* ]]; then
  echo "Using DATABASE_URL from .env (Supabase)"
elif [[ -n "${SUPABASE_DB_PASSWORD:-}" ]]; then
  export USE_SUPABASE_DB=true
  ENCODED_PW="$(python3 -c "import urllib.parse; print(urllib.parse.quote('''${SUPABASE_DB_PASSWORD}'''))")"
  export DATABASE_URL="postgresql://postgres:${ENCODED_PW}@db.${PROJECT_REF}.supabase.co:5432/postgres"
else
  echo "ERROR: Set DATABASE_URL to your Supabase connection string, or SUPABASE_DB_PASSWORD"
  exit 1
fi

export USE_SUPABASE_DB=true

echo "==> Testing Supabase Postgres connection..."
cd "$ROOT/backend"
uv run python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)
with e.connect() as c:
    v = c.execute(text('SELECT version()')).scalar()
    print('Connected:', v[:60], '...')
"

echo "==> Enabling pgvector extension..."
uv run python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    c.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    c.commit()
print('vector extension OK')
"

echo "==> Running Alembic migrations..."
uv run alembic upgrade head

echo "==> Seeding Canadian demo data..."
uv run python scripts/seed.py

echo ""
echo "✅ Supabase setup complete!"
echo "   Tables: users, accounts, transactions, transaction_embeddings, chat_sessions"
echo "   Demo user: demo@finsight.ai"
echo ""
echo "Next: restart backend so it picks up USE_SUPABASE_DB=true"
echo "  cd backend && uv run uvicorn app.main:app --reload --port 8000"
