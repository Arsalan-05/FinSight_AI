import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import agent._warn  # noqa: F401 — suppress third-party import warnings
from app.config import settings
from app.logging_config import configure_logging
from app.middleware.api_key import ApiKeyMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import (
    accounts,
    audit,
    auth,
    budgets,
    capabilities,
    chat,
    dashboard,
    evals_api,
    goals,
    insights,
    integrations,
    leaks,
    notifications,
    planner,
    search,
    transactions,
    users,
)
from db.base import DATABASE_URL, engine
from integrations.plaid_background import plaid_sync_loop, weekly_digest_loop
from mcp import register_mcp_tools


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging(environment=settings.environment, log_level=settings.log_level)
    tools = register_mcp_tools()
    _app.state.mcp_tools = tools
    sync_task = asyncio.create_task(plaid_sync_loop())
    digest_task = asyncio.create_task(weekly_digest_loop())
    try:
        yield
    finally:
        sync_task.cancel()
        digest_task.cancel()


app = FastAPI(
    title="FinSight AI",
    version=settings.app_version,
    lifespan=lifespan,
    # Prevent /path/ → /path redirects. Through the Next /backend proxy those
    # Location headers strip the /backend prefix and break the browser call.
    redirect_slashes=False,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        None
        if settings.environment == "production"
        else r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.\d+\.\d+\.\d+):\d+"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.finsight_api_key:
    app.add_middleware(ApiKeyMiddleware, api_key=settings.finsight_api_key)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(search.router)
app.include_router(insights.router)
app.include_router(goals.router)
app.include_router(chat.router)
app.include_router(integrations.router)
app.include_router(capabilities.router)
app.include_router(budgets.router)
app.include_router(notifications.router)
app.include_router(planner.router)
app.include_router(leaks.router)
app.include_router(audit.router)
app.include_router(evals_api.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
    }


@app.get("/health/ready")
def health_ready() -> dict[str, object]:
    """Readiness probe — verifies database connectivity."""
    connected = False
    error: Optional[str] = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connected = True
    except Exception as exc:
        error = exc.__class__.__name__
    status = "ok" if connected else "degraded"
    return {"status": status, "database": connected, "error": error}


@app.get("/health/db")
def health_db() -> dict[str, object]:
    """Report Postgres connectivity (no secrets)."""
    url = DATABASE_URL
    host = url.split("@")[-1].split("/")[0] if "@" in url else "unknown"
    connected = False
    schema_ready = False
    error: Optional[str] = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            connected = True
            row = conn.execute(
                text(
                    "SELECT EXISTS ("
                    " SELECT 1 FROM information_schema.tables"
                    " WHERE table_schema = 'public' AND table_name = 'users'"
                    ")"
                )
            ).scalar()
            schema_ready = bool(row)
    except Exception as exc:
        error = exc.__class__.__name__

    using_fallback = settings.using_supabase_postgres and "supabase" not in host
    return {
        "connected": connected,
        "schema_ready": schema_ready,
        "using_supabase_postgres": settings.using_supabase_postgres and not using_fallback,
        "using_fallback": using_fallback,
        "use_supabase_db": settings.use_supabase_db,
        "host": host,
        "error": error,
    }


@app.get("/health/auth")
def health_auth() -> dict[str, object]:
    """Report whether Supabase JWKS is reachable (no secrets, no user token)."""
    import urllib.request

    configured = settings.supabase_auth_enabled
    jwks_ok = False
    jwks_error: Optional[str] = None
    jwks_keys = 0
    if settings.supabase_url:
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            with urllib.request.urlopen(jwks_url, timeout=8) as resp:
                import json

                payload = json.loads(resp.read().decode())
                keys = payload.get("keys") or []
                jwks_keys = len(keys) if isinstance(keys, list) else 0
                jwks_ok = jwks_keys > 0
        except Exception as exc:
            jwks_error = exc.__class__.__name__
    return {
        "supabase_auth_configured": configured,
        "jwt_secret_configured": bool(settings.supabase_jwt_secret),
        "jwks_ok": jwks_ok,
        "jwks_keys": jwks_keys,
        "jwks_error": jwks_error,
        "require_auth": settings.require_auth,
        "auth_enforced": settings.auth_enforced,
        "beta_allowlist_enabled": bool(settings.beta_allowed_emails.strip()),
    }
