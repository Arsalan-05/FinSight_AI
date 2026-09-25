from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from db.models import User

logger = logging.getLogger(__name__)


def _check_beta_access(email: str) -> None:
    allowed_raw = settings.beta_allowed_emails.strip()
    if not allowed_raw or not email:
        return
    allowed = {e.strip().lower() for e in allowed_raw.split(",") if e.strip()}
    if email.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="FinSight is in invite-only beta. Contact support for access.",
        )


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase URL is not configured on the server",
        )
    from urllib.parse import urlparse

    raw = settings.supabase_url.strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SUPABASE_URL on the API service is invalid. "
                "Set it to https://YOUR_PROJECT.supabase.co (no quotes)."
            ),
        )
    jwks_url = f"{parsed.scheme}://{parsed.netloc}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def _token_alg(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        return ""
    alg = header.get("alg")
    return str(alg) if alg else ""


def _decode_supabase_token(token: str) -> dict[str, Any]:
    """Verify Supabase user JWTs — ES256 via JWKS (new) or HS256 via shared secret (legacy)."""
    if not settings.supabase_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured on the server",
        )

    alg = _token_alg(token)
    try:
        # Prefer algorithm declared in the token. New Supabase projects use ES256
        # even when a legacy JWT secret env var is still present on Railway.
        if alg in {"ES256", "RS256"} or not settings.supabase_jwt_secret:
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )

        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.info("JWT validation failed (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("JWT validation crashed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth verification unavailable ({type(exc).__name__})",
        ) from exc


def _sync_user_from_claims(db: Session, claims: dict[str, Any]) -> User:
    auth_id = claims.get("sub")
    if not auth_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    email = str(claims.get("email") or "")
    raw_meta = claims.get("user_metadata")
    metadata = raw_meta if isinstance(raw_meta, dict) else {}
    name = str(
        metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@")[0] if email else "User")
    )

    try:
        user = db.query(User).filter(User.auth_id == str(auth_id)).first()
        if user:
            dirty = False
            if email and user.email != email:
                user.email = email
                dirty = True
            if name and user.name != name:
                user.name = name
                dirty = True
            if dirty:
                db.commit()
                db.refresh(user)
            _check_beta_access(email)
            return user

        if email:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.auth_id = str(auth_id)
                if name:
                    existing.name = name
                db.commit()
                db.refresh(existing)
                _check_beta_access(email)
                return existing

        _check_beta_access(email)
        user = User(
            auth_id=str(auth_id),
            email=email or f"{auth_id}@supabase.local",
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("User sync DB error")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error during auth ({type(exc).__name__})",
        ) from exc
    except Exception as exc:
        logger.exception("User sync crashed")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auth sync failed ({type(exc).__name__})",
        ) from exc


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
        if settings.auth_enforced:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return None
    if not settings.supabase_auth_enabled:
        if settings.auth_enforced:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase auth is not configured on the server",
            )
        return None
    token = authorization[7:].strip()
    claims = _decode_supabase_token(token)
    return _sync_user_from_claims(db, claims)
