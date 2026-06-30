from __future__ import annotations

import json
from datetime import date
from typing import Any

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from agent.tools.aggregator import aggregate_spending
from agent.tools.dates import last_month_range, resolve_aggregate_dates
from agent.tools.summarize import is_empty_aggregate, summarize_aggregate
from agent.tools.web_search import search_web
from app.config import settings
from insights.runway import analyze_cash_runway
from insights.service import build_all_insights
from insights.tfsa import tfsa_contribution_status
from mcp.registry import MCP_TOOL_DEFINITIONS, execute_mcp_tool
from rag.retriever import retrieve

CORE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_transactions",
        "description": (
            "Semantic search over transaction history. Use for natural-language queries "
            "like 'coffee shops last month' or 'subscription payments'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "aggregate_spending",
        "description": (
            "SQL aggregate over transactions — totals, counts, grouped by category, "
            "merchant, or month. Use for ALL 'how much did I spend' questions. "
            "Set period='last_month' for 'last month' questions (do not guess dates)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["last_month", "this_month", "last_30_days", "all"],
                    "description": (
                        "Relative time window. Use last_month when the user says 'last month'. "
                        "Prefer this over start_date/end_date."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD). Only if period is not set.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD). Only if period is not set.",
                },
                "group_by": {
                    "type": "string",
                    "enum": ["category", "merchant", "month", "none"],
                    "description": (
                        "Use 'none' for a single total (recommended with category filter)."
                    ),
                    "default": "none",
                },
                "account_id": {
                    "type": "string",
                    "description": "Optional account UUID to filter by.",
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Filter by category name (Dining, Groceries, etc.). "
                        "OMIT this field for all-categories breakdowns — never pass 'none'."
                    ),
                },
                "transaction_type": {
                    "type": "string",
                    "enum": ["all", "debit", "credit"],
                    "description": "Filter debits (expenses), credits (income), or all.",
                    "default": "all",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_user_financial_profile",
        "description": (
            "Get a learned financial fingerprint from the user's transaction history: "
            "spending patterns, top categories/merchants, income vs expenses, and "
            "preferences remembered from past chats. Use for personalized advice."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_web",
        "description": (
            "Search the internet for CURRENT information: tax limits, bank product rates, "
            "investment news, CRA rules, ETF comparisons, or any fact not in the user's "
            "transaction database. Use alongside personal-data tools for complete answers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query — be specific (e.g. '2026 TFSA limit Canada')."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default 5, max 8).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_financial_insights",
        "description": (
            "Get proactive insights: subscriptions, cash runway, TFSA room, anomalies, "
            "credit card tips, and multi-account reconciliation."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_tfsa_status",
        "description": "Check estimated TFSA and RRSP contribution room for the current year.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_cash_runway",
        "description": (
            "Estimate cash runway in months from recent spending (student/co-op friendly)."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

TOOL_DEFINITIONS: list[dict[str, Any]] = CORE_TOOL_DEFINITIONS + MCP_TOOL_DEFINITIONS


def get_tool_definitions() -> list[dict[str, Any]]:
    """All agent tools: core finance tools + MCP + web search."""
    return list(TOOL_DEFINITIONS)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


_INVALID_CATEGORY_VALUES = frozenset({"none", "all", "any", "null", "n/a", ""})


def _normalize_category(value: Any) -> str | None:
    """Drop bogus category values small models pass (e.g. category='none')."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID_CATEGORY_VALUES:
        return None
    return text


def _normalize_account_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID_CATEGORY_VALUES:
        return None
    return text


def _run_aggregate(
    db: Session,
    *,
    start_date: date | None,
    end_date: date | None,
    group_by: str,
    category: str | None,
    account_id: str | None,
    transaction_type: str,
    account_ids: list[str] | None = None,
) -> dict[str, Any]:
    return aggregate_spending(
        db,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,  # type: ignore[arg-type]
        category=category,
        account_id=account_id,
        account_ids=account_ids,
        transaction_type=transaction_type,  # type: ignore[arg-type]
    )


def _format_transaction(tx: Any) -> dict[str, Any]:
    return {
        "id": tx.id,
        "date": tx.transaction_date.isoformat(),
        "description": tx.description,
        "amount": float(tx.amount),
        "category": tx.category,
        "merchant": tx.merchant,
        "account_id": tx.account_id,
    }


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    db: Session,
    account_ids: list[str] | None = None,
) -> str:
    """Execute a named agent tool and return a JSON string result."""
    if name == "search_transactions":
        query = str(args.get("query", ""))
        k = int(args.get("k") or 5)
        if not settings.embeddings_configured:
            return json.dumps(
                {"error": "Semantic search unavailable — embeddings provider not configured."}
            )
        try:
            txs = retrieve(query, db, k=k, account_ids=account_ids)
            return json.dumps(
                {"results": [_format_transaction(tx) for tx in txs], "count": len(txs)}
            )
        except Exception as exc:
            return json.dumps({"error": f"Semantic search failed: {exc}"})

    if name == "aggregate_spending":
        start_date, end_date = resolve_aggregate_dates(args)
        category = _normalize_category(args.get("category"))
        account_id = _normalize_account_id(args.get("account_id"))
        txn_type = str(args.get("transaction_type") or "all")
        group_by = str(args.get("group_by") or ("none" if category else "category"))

        result = _run_aggregate(
            db,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            category=category,
            account_id=account_id,
            transaction_type=txn_type,
            account_ids=account_ids,
        )
        if args.get("period"):
            result["filters"]["period"] = args["period"]

        if is_empty_aggregate(result):
            retry_start, retry_end = last_month_range()
            result = _run_aggregate(
                db,
                start_date=retry_start,
                end_date=retry_end,
                group_by="none" if category else "category",
                category=category,
                account_id=None,
                transaction_type="debit",
                account_ids=account_ids,
            )
            result["filters"]["period"] = "last_month"
            result["auto_retried"] = True

        result["summary"] = summarize_aggregate(result)
        return json.dumps(result)

    if name == "get_financial_insights":
        return json.dumps(build_all_insights(db, account_ids=account_ids))

    if name == "get_user_financial_profile":
        from agent.user_profile import (
            build_data_profile,
            load_agent_profile,
            profile_narrative,
        )

        if account_ids is not None and not account_ids:
            return json.dumps({"error": "No accounts linked.", "data_profile": {}})
        data = build_data_profile(db, account_ids=account_ids)
        learned: dict[str, Any] = {}
        if account_ids:
            from db.models import Account

            acct = db.query(Account).filter(Account.id.in_(account_ids)).first()
            if acct and acct.user:
                learned = load_agent_profile(acct.user)
        return json.dumps(
            {
                "data_profile": data,
                "learned_profile": learned,
                "summary": profile_narrative(data, learned),
            }
        )

    if name == "search_web":
        query = str(args.get("query", ""))
        max_results = int(args.get("max_results") or 5)
        return json.dumps(search_web(query, max_results=max_results))

    if name == "get_tfsa_status":
        return json.dumps(tfsa_contribution_status(db, account_ids=account_ids))

    if name == "get_cash_runway":
        return json.dumps(analyze_cash_runway(db, account_ids=account_ids))

    if name in {"convert_currency", "get_market_quote", "get_exchange_rates"}:
        return execute_mcp_tool(name, args)

    return json.dumps({"error": f"Unknown tool: {name}"})


def build_langchain_tools(db: Session) -> list[StructuredTool]:
    """LangChain StructuredTool wrappers (used by ToolNode if needed)."""

    def search_transactions(query: str, k: int = 5) -> str:
        return execute_tool("search_transactions", {"query": query, "k": k}, db=db)

    def aggregate_spending_tool(
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: str = "category",
        account_id: str | None = None,
        transaction_type: str = "all",
    ) -> str:
        return execute_tool(
            "aggregate_spending",
            {
                "start_date": start_date,
                "end_date": end_date,
                "group_by": group_by,
                "account_id": account_id,
                "transaction_type": transaction_type,
            },
            db=db,
        )

    return [
        StructuredTool.from_function(
            func=search_transactions,
            name="search_transactions",
            description=TOOL_DEFINITIONS[0]["description"],
        ),
        StructuredTool.from_function(
            func=aggregate_spending_tool,
            name="aggregate_spending",
            description=TOOL_DEFINITIONS[1]["description"],
        ),
    ]
