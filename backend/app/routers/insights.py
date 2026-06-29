from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.dependencies import get_db
from app.scoping import account_ids_for_user
from db.models import User
from insights.service import build_all_insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/")
def get_insights(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Proactive financial insights: subscriptions, runway, TFSA, anomalies, credit tips."""
    account_ids = account_ids_for_user(db, current_user)
    return build_all_insights(db, account_ids=account_ids)
