from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import agent._warn  # noqa: F401 — suppress third-party import warnings
from app.config import settings
from app.middleware.api_key import ApiKeyMiddleware
from app.routers import accounts, auth, chat, search, transactions, users
from mcp import register_mcp_tools


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    tools = register_mcp_tools()
    _app.state.mcp_tools = tools
    yield


app = FastAPI(title="FinSight AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
