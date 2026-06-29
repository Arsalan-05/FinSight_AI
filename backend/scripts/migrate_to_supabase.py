"""Copy data from local Docker Postgres to Supabase Postgres.

Usage (both DBs must be reachable):
  USE_SUPABASE_DB=false uv run python scripts/migrate_to_supabase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from db.models import Account, ChatSession, Transaction, TransactionEmbedding, User


def _local_url() -> str:
    return settings.database_url


def _supabase_url() -> str:
    if not settings.supabase_db_password or not settings.supabase_url:
        raise SystemExit("Set SUPABASE_DB_PASSWORD and SUPABASE_URL in .env")
    ref = settings.supabase_url.rstrip("/").replace("https://", "").replace(".supabase.co", "")
    pwd = quote_plus(settings.supabase_db_password)
    return f"postgresql://postgres:{pwd}@db.{ref}.supabase.co:5432/postgres"


def migrate() -> None:
    local = sessionmaker(bind=create_engine(_local_url()))()
    remote_engine = create_engine(_supabase_url())
    remote = sessionmaker(bind=remote_engine)()

    with remote_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    tables = [User, Account, Transaction, TransactionEmbedding, ChatSession]
    for model in tables:
        rows = local.query(model).all()
        print(f"Copying {len(rows)} {model.__tablename__} rows...")
        for row in rows:
            remote.merge(row)
        remote.commit()

    print("Done — local data copied to Supabase.")


if __name__ == "__main__":
    migrate()
