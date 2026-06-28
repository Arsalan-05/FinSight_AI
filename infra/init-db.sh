#!/usr/bin/env bash
# Runs Alembic migrations inside the api container.
# Usage: docker compose exec api bash infra/init-db.sh
set -euo pipefail

cd /app
uv run alembic upgrade head
echo "Migrations complete."
