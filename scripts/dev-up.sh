#!/usr/bin/env bash
# One-command local dev bootstrap for FinSight AI
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Postgres (Docker)..."
docker compose up -d db

echo "==> Waiting for database..."
for i in {1..30}; do
  if docker compose exec -T db pg_isready -U finsight >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Running Alembic migrations..."
cd backend
uv run alembic upgrade head

echo ""
echo "==> FinSight local stack ready"
echo "    Database: local Docker Postgres on localhost:5432"
echo ""
echo "    Local dev (recommended):"
echo "      docker compose up -d db          # DB only"
echo "      cd backend && uv run uvicorn app.main:app --reload --port 8000"
echo "      cd frontend && npm run dev"
echo ""
echo "    If port 8000 is in use: docker compose stop api"
echo "    Supabase auth + local Postgres data is normal."
