"""Sliding-window rate limiter for the /chat endpoint."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request

from app.auth import get_current_user_optional
from app.config import settings
from db.models import User


class SlidingWindowRateLimiter:
    """Per-key request cap over a rolling time window."""

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        limit = settings.chat_rate_limit_per_minute
        if limit <= 0:
            return

        now = time.time()
        with self._lock:
            recent = [t for t in self._hits[key] if now - t < self.window_seconds]
            if len(recent) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many chat requests. Please wait a moment and try again.",
                )
            recent.append(now)
            self._hits[key] = recent

    def reset(self) -> None:
        """Clear all counters — used in tests."""
        with self._lock:
            self._hits.clear()


chat_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)


def enforce_chat_rate_limit(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
) -> None:
    """FastAPI dependency: limit chat requests per user or client IP."""
    if settings.chat_rate_limit_per_minute <= 0:
        return

    client = request.client
    client_host = client.host if client else "unknown"
    key = f"user:{current_user.id}" if current_user else f"ip:{client_host}"
    chat_rate_limiter.check(key)
