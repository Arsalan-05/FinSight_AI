from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.goals import add_goal, delete_goal, load_goals
from app.auth import get_current_user_optional
from app.dependencies import get_db
from db.models import User

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    target_amount: float | None = None
    deadline: str | None = None
    notes: str | None = None


def _require_user(user: User | None) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.get("/")
def list_goals(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[dict[str, Any]]:
    user = _require_user(current_user)
    return load_goals(user)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    user = _require_user(current_user)
    return add_goal(
        db,
        user,
        title=payload.title,
        target_amount=payload.target_amount,
        deadline=payload.deadline,
        notes=payload.notes,
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> None:
    user = _require_user(current_user)
    if not delete_goal(db, user, goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
