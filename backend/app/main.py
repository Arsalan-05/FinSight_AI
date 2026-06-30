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
from app.routers import (
    accounts,
    auth,
    budgets,
    capabilities,
    chat,
    goals,
    insights,
    integrations,
    notifications,
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


app = FastAPI(title="FinSight AI", version=settings.app_version, lifespan=lifespan)

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
