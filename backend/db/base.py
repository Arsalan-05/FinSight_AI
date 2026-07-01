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

_engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
_connect_args: dict[str, object] = {"connect_timeout": 8}
_is_supabase_url = "supabase.co" in DATABASE_URL or "pooler.supabase.com" in DATABASE_URL
if _is_supabase_url and "sslmode=" not in DATABASE_URL:
    _connect_args["sslmode"] = "require"
_engine_kwargs["connect_args"] = _connect_args
# Session pooler allows ~15 clients total (shared with Render). Cap pool in all envs.
if _is_supabase_url:
    _engine_kwargs["pool_size"] = settings.db_pool_size
    _engine_kwargs["max_overflow"] = settings.db_max_overflow

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
