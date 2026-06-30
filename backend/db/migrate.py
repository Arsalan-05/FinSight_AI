"""Apply Alembic migrations to the configured Postgres URL (never local fallback)."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.config import settings

logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_migrations() -> None:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    url = settings.database_url_resolved.replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", url)
    host = settings.database_url_resolved.split("@")[-1].split("/")[0]
    logger.info("Running Alembic migrations against %s", host)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
