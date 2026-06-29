from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import agent._warn  # noqa: F401 — suppress third-party import warnings
from app.config import settings
from app.middleware.api_key import ApiKeyMiddleware
from app.routers import accounts, auth, chat, goals, insights, search, transactions, users
from db.base import DATABASE_URL, engine
from mcp import register_mcp_tools


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    tools = register_mcp_tools()
    _app.state.mcp_tools = tools
    yield


app = FastAPI(title="FinSight AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|172\.\d+\.\d+\.\d+):\d+",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/health/db")
def health_db() -> dict[str, object]:
    """Report Postgres connectivity (no secrets)."""
    url = DATABASE_URL
    host = url.split("@")[-1].split("/")[0] if "@" in url else "unknown"
    connected = False
    error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        connected = True
    except Exception as exc:
        error = exc.__class__.__name__

    using_fallback = settings.using_supabase_postgres and "supabase" not in host
    return {
        "connected": connected,
        "using_supabase_postgres": settings.using_supabase_postgres and not using_fallback,
        "using_fallback": using_fallback,
        "use_supabase_db": settings.use_supabase_db,
        "host": host,
        "error": error,
    }
