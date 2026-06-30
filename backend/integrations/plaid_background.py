"""Background Plaid sync — periodic pull for all active connections."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import SessionLocal
from db.models import BankConnection
from integrations.plaid_client import plaid_configured
from integrations.plaid_sync import sync_connection

logger = logging.getLogger(__name__)


def sync_all_active_connections(db: Session) -> int:
    """Sync every active bank connection. Returns count synced."""
    if not plaid_configured():
        return 0
    connections = (
        db.query(BankConnection).filter(BankConnection.status == "active").all()
    )
    synced = 0
    for conn in connections:
        try:
            sync_connection(db, conn)
            synced += 1
        except Exception:
            logger.exception("Plaid background sync failed for connection %s", conn.id)
    return synced


async def plaid_sync_loop() -> None:
    """Run periodic Plaid sync while the API process is alive."""
    interval = max(300, settings.plaid_sync_interval_seconds)
    while True:
        await asyncio.sleep(interval)
        if not plaid_configured():
            continue
        db = SessionLocal()
        try:
            count = sync_all_active_connections(db)
            if count:
                logger.info("Plaid background sync completed for %s connection(s)", count)
        finally:
            db.close()


async def weekly_digest_loop() -> None:
    """Send weekly email digests once per day when SMTP is configured."""
    from notifications.digest import send_pending_weekly_digests

    while True:
        await asyncio.sleep(86_400)
        if not settings.smtp_host:
            continue
        db = SessionLocal()
        try:
            send_pending_weekly_digests(db)
        except Exception:
            logger.exception("Weekly digest job failed")
        finally:
            db.close()
