"""Auth API — sync Supabase users with the app database."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from agent.user_profile import _EMPTY_PROFILE, load_agent_profile, save_agent_profile
from app.auth import get_current_user
from app.demo_provision import ensure_user_has_data
from app.dependencies import get_db
from app.schemas import BootstrapOut, UserOut
from app.user_data import delete_user_and_data, export_user_data
from db.base import DATABASE_URL, engine
from db.models import Account, Transaction, User
from notifications.digest import send_weekly_digest_to_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    """Return the app user linked to the Supabase JWT."""
    return user


@router.post("/sync", response_model=UserOut)
def sync_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Ensure the Supabase identity has a matching row and starter demo data."""
    ensure_user_has_data(db, user)
    db.refresh(user)
    return user


@router.post("/bootstrap", response_model=BootstrapOut)
def bootstrap(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BootstrapOut:
    """Sync user, provision data if empty, return DB + counts for the dashboard."""
    provisioned = ensure_user_has_data(db, user)
    db.refresh(user)

    db_connected = False
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        db_error = exc.__class__.__name__

    host = DATABASE_URL.split("@")[-1].split("/")[0] if "@" in DATABASE_URL else "unknown"
    using_fallback = "supabase" not in host and "pooler" not in host

    account_count = db.query(Account).filter(Account.user_id == user.id).count()
    tx_count = (
        db.query(Transaction).join(Account).filter(Account.user_id == user.id).count()
    )

    return BootstrapOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        provisioned_demo=provisioned,
        db_connected=db_connected,
        db_host=host,
        using_fallback=using_fallback,
        db_error=db_error,
        account_count=account_count,
        transaction_count=tx_count,
    )


@router.get("/me/export")
def export_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Download all user data as JSON."""
    return export_user_data(db, user)


@router.get("/me/profile")
def get_learned_profile(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Return what the finance advisor has learned about this user."""
    return load_agent_profile(user)


@router.delete("/me/profile", status_code=status.HTTP_204_NO_CONTENT)
def clear_learned_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Clear the advisor's learned profile (conversation memory)."""
    save_agent_profile(db, user, dict(_EMPTY_PROFILE))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the authenticated user and all financial data."""
    delete_user_and_data(db, user)


@router.post("/me/send-digest")
def send_digest_now(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Trigger a weekly money brief email for the current user (beta testing)."""
    sent = send_weekly_digest_to_user(db, user)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Email digest not sent — enable email_digest in alert preferences "
                "and configure SMTP."
            ),
        )
    return {"sent": True}
