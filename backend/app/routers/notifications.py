"""In-app notifications and alert preferences."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependencies import get_db
from app.schemas import AlertPreferencesIn, AlertPreferencesOut, NotificationOut
from db.models import Notification, User
from notifications.alerts import check_budget_alerts

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _prefs_out(user: User) -> AlertPreferencesOut:
    try:
        data = json.loads(user.alert_prefs_json or "{}")
    except json.JSONDecodeError:
        data = {}
    return AlertPreferencesOut(
        spend_alerts=bool(data.get("spend_alerts", True)),
        email_digest=bool(data.get("email_digest", False)),
    )


@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Notification]:
    check_budget_alerts(db, current_user)
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    note = db.get(Notification, notification_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.read = True
    db.commit()
    db.refresh(note)
    return note


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read.is_(False),
    ).update({"read": True})
    db.commit()


@router.get("/preferences", response_model=AlertPreferencesOut)
def get_preferences(current_user: User = Depends(get_current_user)) -> AlertPreferencesOut:
    return _prefs_out(current_user)


@router.patch("/preferences", response_model=AlertPreferencesOut)
def update_preferences(
    payload: AlertPreferencesIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertPreferencesOut:
    try:
        data = json.loads(current_user.alert_prefs_json or "{}")
    except json.JSONDecodeError:
        data = {}
    if payload.spend_alerts is not None:
        data["spend_alerts"] = payload.spend_alerts
    if payload.email_digest is not None:
        data["email_digest"] = payload.email_digest
    current_user.alert_prefs_json = json.dumps(data)
    db.commit()
    db.refresh(current_user)
    return _prefs_out(current_user)
