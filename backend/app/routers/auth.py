"""Auth API — sync Supabase users with the app database."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.demo_provision import ensure_user_has_data
from app.dependencies import get_db
from app.schemas import BootstrapOut, UserOut
from db.base import DATABASE_URL, engine
from db.models import Account, Transaction, User

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
