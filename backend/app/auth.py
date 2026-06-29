from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from db.models import User

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase URL is not configured on the server",
        )
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def _decode_supabase_token(token: str) -> dict[str, Any]:
    """Verify Supabase user JWTs — ES256 via JWKS (new) or HS256 via shared secret (legacy)."""
    if not settings.supabase_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured on the server",
        )

    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def _sync_user_from_claims(db: Session, claims: dict[str, Any]) -> User:
    auth_id = claims.get("sub")
    if not auth_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    email = str(claims.get("email") or "")
    metadata = claims.get("user_metadata") or {}
    name = (
        metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@")[0] if email else "User")
    )

    user = db.query(User).filter(User.auth_id == auth_id).first()
    if user:
        if email and user.email != email:
            user.email = email
        if name and user.name != name:
            user.name = name
            db.commit()
            db.refresh(user)
        return user

    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.auth_id = auth_id
            if name:
                existing.name = name
            db.commit()
            db.refresh(existing)
            return existing

    user = User(auth_id=auth_id, email=email or f"{auth_id}@supabase.local", name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """Require a valid Supabase JWT and return the linked app user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization[7:].strip()
    claims = _decode_supabase_token(token)
    return _sync_user_from_claims(db, claims)


def get_current_user_optional(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User | None:
    """Return linked user when a valid JWT is present; None in open dev mode."""
    if not authorization or not authorization.startswith("Bearer "):
        if settings.require_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return None
    token = authorization[7:].strip()
    claims = _decode_supabase_token(token)
    return _sync_user_from_claims(db, claims)
