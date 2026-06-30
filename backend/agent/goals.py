"""User financial goals — persisted for agent memory."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models import User


def load_goals(user: User) -> list[dict[str, Any]]:
    try:
        data = json.loads(user.goals_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_goals(db: Session, user: User, goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user.goals_json = json.dumps(goals)
    db.commit()
    db.refresh(user)
    return goals


def add_goal(
    db: Session,
    user: User,
    *,
    title: str,
    target_amount: float | None = None,
    deadline: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    goals = load_goals(user)
    goal = {
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "target_amount": target_amount,
        "deadline": deadline,
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
    }
    goals.append(goal)
    save_goals(db, user, goals)
    return goal


def delete_goal(db: Session, user: User, goal_id: str) -> bool:
    goals = load_goals(user)
    new_goals = [g for g in goals if g.get("id") != goal_id]
    if len(new_goals) == len(goals):
        return False
    save_goals(db, user, new_goals)
    return True


def update_goal(
    db: Session,
    user: User,
    goal_id: str,
    *,
    title: str | None = None,
    target_amount: float | None = None,
    current_amount: float | None = None,
    deadline: str | None = None,
    notes: str | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    goals = load_goals(user)
    for goal in goals:
        if goal.get("id") != goal_id:
            continue
        if title is not None:
            goal["title"] = title.strip()
        if target_amount is not None:
            goal["target_amount"] = target_amount
        if current_amount is not None:
            goal["current_amount"] = current_amount
        if deadline is not None:
            goal["deadline"] = deadline
        if notes is not None:
            goal["notes"] = notes
        if status is not None:
            goal["status"] = status
        goal["updated_at"] = datetime.utcnow().isoformat()
        save_goals(db, user, goals)
        return goal
    return None


def goals_summary_for_prompt(user: User) -> str:
    goals = load_goals(user)
    if not goals:
        return ""
    lines = ["User financial goals:"]
    for g in goals:
        if g.get("status") != "active":
            continue
        line = f"- {g['title']}"
        if g.get("target_amount"):
            line += f" (target ${g['target_amount']:,.0f}"
            if g.get("current_amount") is not None:
                line += f", ${g['current_amount']:,.0f} saved"
            line += ")"
        elif g.get("current_amount") is not None:
            line += f" (${g['current_amount']:,.0f} saved)"
        if g.get("deadline"):
            line += f" by {g['deadline']}"
        lines.append(line)
    return "\n".join(lines)
