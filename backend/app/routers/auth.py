"""Auth API — sync Supabase users with the app database."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependencies import get_db
from app.schemas import UserOut
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    """Return the app user linked to the Supabase JWT."""
    return user


@router.post("/sync", response_model=UserOut)
def sync_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Ensure the Supabase identity has a matching row in the app database."""
    db.refresh(user)
    return user
