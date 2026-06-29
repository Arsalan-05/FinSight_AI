from __future__ import annotations

from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

from agent.runner import run_agent
from db.base import SessionLocal

AgentRunner = Callable[..., str]


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_agent_runner() -> AgentRunner:
    """FastAPI dependency — returns the agent runner callable."""
    return run_agent
