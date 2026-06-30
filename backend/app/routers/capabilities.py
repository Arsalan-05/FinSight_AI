"""Public capability manifest — proves what the backend ships."""

from __future__ import annotations

from fastapi import APIRouter

from agent.tools import get_tool_definitions
from app.config import settings
from db.base import DATABASE_URL
from integrations.plaid_client import plaid_configured

router = APIRouter(tags=["meta"])


@router.get("/capabilities")
def capabilities() -> dict[str, object]:
    tools = get_tool_definitions()
    return {
        "product": "FinSight AI",
        "version": settings.app_version,
        "environment": settings.environment,
        "stack": {
            "api": "FastAPI",
            "agent": "LangGraph ReAct",
            "database": "PostgreSQL + pgvector",
            "auth": "Supabase JWT",
            "llm": settings.llm_provider,
            "embeddings": settings.embedding_provider,
        },
        "agent": {
            "tool_count": len(tools),
            "tools": [t["name"] for t in tools],
            "features": [
                "multi-step_react_loop",
                "parallel_tool_execution",
                "session_memory",
                "user_profile_learning",
                "web_search",
                "live_market_quotes",
                "transaction_rag",
                "sql_aggregates",
                "sse_streaming",
            ],
            "max_tool_rounds": 18,
        },
        "integrations": {
            "plaid_bank_link": plaid_configured(),
            "web_search": settings.web_search_enabled,
            "tavily": bool(settings.tavily_api_key),
            "finnhub": bool(settings.finnhub_api_key),
        },
        "reliability": [
            "rate_limiting",
            "request_id_middleware",
            "health_ready_probe",
            "structured_logging_production",
            "per_user_data_scoping",
        ],
        "beta": {
            "invite_only": bool(settings.beta_allowed_emails.strip()),
        },
        "ops": {
            "database_host": (
                DATABASE_URL.split("@")[-1].split("/")[0] if "@" in DATABASE_URL else "local"
            ),
            "plaid_configured": plaid_configured(),
            "smtp_configured": bool(settings.smtp_host and settings.smtp_from),
            "embeddings_configured": settings.embeddings_configured,
            "llm_configured": settings.llm_configured,
            "auth_enforced": settings.auth_enforced,
        },
    }
