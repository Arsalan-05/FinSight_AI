from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


def _pick_database_url() -> str:
    primary = settings.database_url_resolved
    if not settings.using_supabase_postgres or not settings.database_fallback_enabled:
        return primary

    try:
        probe = create_engine(primary, connect_args={"connect_timeout": 4})
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary
    except Exception as exc:
        fallback = settings.database_fallback_url
        logger.warning(
            "Supabase Postgres unreachable (%s). Using local fallback: %s",
            exc.__class__.__name__,
            fallback.split("@")[-1],
        )
        return fallback


DATABASE_URL = _pick_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
