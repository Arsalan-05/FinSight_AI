"""Weekly money brief email delivery."""

from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.scoping import account_ids_for_user
from db.models import User
from insights.service import build_weekly_brief
from notifications.email import send_email

logger = logging.getLogger(__name__)


def _wants_digest(user: User) -> bool:
    try:
        prefs = json.loads(user.alert_prefs_json or "{}")
    except json.JSONDecodeError:
        return False
    return bool(prefs.get("email_digest", False))


def send_weekly_digest_to_user(db: Session, user: User) -> bool:
    if not user.email or not _wants_digest(user):
        return False
    account_ids = account_ids_for_user(db, user)
    brief = build_weekly_brief(db, account_ids=account_ids)
    lines = [brief["headline"], ""]
    for section in brief.get("sections", []):
        lines.append(f"• {section['label']}: {section['value']}")
    if brief.get("alerts"):
        lines.append("")
        lines.append("Alerts:")
        for alert in brief["alerts"]:
            lines.append(f"• {alert['title']}: {alert['body']}")
    body = "\n".join(lines)
    subject = f"Your FinSight weekly brief — {date.today().strftime('%b %d')}"
    return send_email(user.email, subject, body)


def send_pending_weekly_digests(db: Session) -> int:
    """Send digest on Mondays (or if never sent this week)."""
    if not settings.smtp_host:
        return 0
    if date.today().weekday() != 0:
        return 0
    sent = 0
    for user in db.query(User).all():
        try:
            if send_weekly_digest_to_user(db, user):
                sent += 1
        except Exception:
            logger.exception("Failed weekly digest for user %s", user.id)
    return sent
