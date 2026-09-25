from __future__ import annotations

import json
from datetime import date
from typing import Any

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from agent.tools.aggregator import aggregate_spending
from agent.tools.calculate import calculate
from agent.tools.categories import normalize_category as _normalize_category
from agent.tools.coverage import attach_coverage, latest_month_with_spend
from agent.tools.dates import last_month_range, resolve_aggregate_dates
from agent.tools.summarize import is_empty_aggregate, summarize_aggregate
from agent.tools.web_search import search_web
from app.config import settings
from insights.runway import analyze_cash_runway
from insights.service import build_all_insights
from insights.tfsa import tfsa_contribution_status
from mcp.registry import MCP_TOOL_DEFINITIONS, execute_mcp_tool
from planning.forecast import run_cash_forecast
from planning.osap import plan_osap
from planning.registered import optimize_registered
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
            "Set period='last_month' for 'last month' (do not guess dates). "
            "For dining/restaurants/eating out/takeout use category=Dining. "
            "If the window is empty, the summary includes your data date range — "
            "tell the user in plain English; never invent numbers."
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
                        "Canonical category: Dining, Groceries, Transport, "
                        "Subscriptions, Utilities, Rent, Income, Transfers, Bank Fees. "
                        "Synonyms (restaurants, eating out, takeout) map to Dining. "
                        "OMIT for all-categories — never pass 'none'."
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
    {
        "name": "calculate",
        "description": (
            "Safely evaluate a simple arithmetic expression (+, -, *, /, parentheses). "
            "Use for ALL mental math — never compute sums, differences, or percentages yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression, e.g. '(412.30 + 88.50) * 0.13'.",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "run_registered_optimizer",
        "description": (
            "Optimize FHSA/TFSA/RRSP contribution allocation with a year-by-year projection. "
            "Use for Canadian registered-account planning questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "income": {
                    "type": "number",
                    "description": "Annual earned income in CAD.",
                },
                "age": {"type": "integer", "description": "Current age."},
                "first_time_buyer": {
                    "type": "boolean",
                    "description": "Whether the user is a first-time home buyer (FHSA eligible).",
                    "default": False,
                },
                "horizon": {
                    "type": "integer",
                    "description": "Projection horizon in years (default 5).",
                    "default": 5,
                },
                "annual_contribution": {
                    "type": "number",
                    "description": "Dollars available to contribute each year.",
                    "default": 0,
                },
                "existing_room": {
                    "type": "object",
                    "description": "Unused room: tfsa, rrsp, fhsa, fhsa_lifetime_contributed.",
                },
                "tax_year": {
                    "type": "integer",
                    "description": "Starting calendar year for CRA limits (default 2026).",
                    "default": 2026,
                },
            },
            "required": ["income", "age"],
        },
    },
    {
        "name": "run_osap_plan",
        "description": (
            "Compare OSAP / student loan repayment: standard vs accelerated amortization "
            "and the effect of extra monthly payments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "principal": {
                    "type": "number",
                    "description": "Outstanding loan balance in CAD.",
                },
                "annual_rate": {
                    "type": "number",
                    "description": "Optional annual interest rate override (e.g. 0.055).",
                },
                "standard_years": {
                    "type": "number",
                    "description": "Standard amortization years (default from rules).",
                },
                "accelerated_years": {
                    "type": "number",
                    "description": "Accelerated amortization years.",
                },
                "extra_monthly": {
                    "type": "number",
                    "description": "Extra dollars paid each month on top of standard payment.",
                    "default": 0,
                },
                "tax_year": {
                    "type": "integer",
                    "description": "Year for default OSAP parameters (default 2026).",
                    "default": 2026,
                },
            },
            "required": ["principal"],
        },
    },
    {
        "name": "run_cash_forecast",
        "description": (
            "Monte Carlo cash forecast: P10/P50/P90 ending balances and probability of ruin. "
            "Educational estimate only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "starting_balance": {"type": "number"},
                "monthly_income_mean": {"type": "number"},
                "monthly_expense_mean": {"type": "number"},
                "monthly_income_std": {"type": "number", "default": 0},
                "monthly_expense_std": {"type": "number", "default": 0},
                "months": {"type": "integer", "default": 12},
                "n_sims": {
                    "type": "integer",
                    "description": "Number of simulations (default 5000).",
                    "default": 5000,
                },
                "seed": {"type": "integer", "description": "Optional RNG seed."},
                "ruin_threshold": {
                    "type": "number",
                    "description": "Balance below which a path counts as ruin (default 0).",
                    "default": 0,
                },
            },
            "required": [
                "starting_balance",
                "monthly_income_mean",
                "monthly_expense_mean",
            ],
        },
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


def _finalize_aggregate(
    result: dict[str, Any],
    db: Session,
    *,
    account_ids: list[str] | None,
    category: str | None,
) -> str:
    attach_coverage(result, db, account_ids=account_ids, category=category)
    result["summary"] = summarize_aggregate(result)
    return json.dumps(result)


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

        # 1) Wrong absolute dates → calendar last month (debits)
        if is_empty_aggregate(result):
            retry_start, retry_end = last_month_range()
            same_window = start_date == retry_start and end_date == retry_end
            if not same_window or txn_type != "debit" or account_id:
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

        # 2) Asked window truly empty but history exists → nearest month with spend
        if is_empty_aggregate(result):
            nearest = latest_month_with_spend(
                db,
                account_ids=account_ids,
                category=category,
                transaction_type="debit",
            )
            if nearest:
                near_start, near_end = nearest
                result = _run_aggregate(
                    db,
                    start_date=near_start,
                    end_date=near_end,
                    group_by="none" if category else "category",
                    category=category,
                    account_id=None,
                    transaction_type="debit",
                    account_ids=account_ids,
                )
                result["filters"]["period"] = "nearest_month_with_data"
                result["broadened"] = True
                result["auto_retried"] = True

        return _finalize_aggregate(
            result, db, account_ids=account_ids, category=category
        )

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

    if name == "calculate":
        expression = str(args.get("expression", ""))
        return json.dumps(calculate(expression))

    if name == "run_registered_optimizer":
        try:
            room = args.get("existing_room")
            result = optimize_registered(
                income=float(args.get("income", 0)),
                age=int(args.get("age", 0)),
                first_time_buyer=bool(args.get("first_time_buyer", False)),
                horizon=int(args.get("horizon") or 5),
                existing_room=room if isinstance(room, dict) else None,
                annual_contribution=float(args.get("annual_contribution") or 0),
                tax_year=int(args.get("tax_year") or 2026),
            )
            return json.dumps(result)
        except (TypeError, ValueError, FileNotFoundError) as exc:
            return json.dumps({"error": str(exc)})

    if name == "run_osap_plan":
        try:
            rate = args.get("annual_rate")
            std_y = args.get("standard_years")
            accel_y = args.get("accelerated_years")
            result = plan_osap(
                principal=float(args.get("principal", 0)),
                annual_rate=float(rate) if rate is not None else None,
                standard_years=float(std_y) if std_y is not None else None,
                accelerated_years=float(accel_y) if accel_y is not None else None,
                extra_monthly=float(args.get("extra_monthly") or 0),
                tax_year=int(args.get("tax_year") or 2026),
            )
            return json.dumps(result)
        except (TypeError, ValueError, FileNotFoundError) as exc:
            return json.dumps({"error": str(exc)})

    if name == "run_cash_forecast":
        try:
            seed = args.get("seed")
            result = run_cash_forecast(
                starting_balance=float(args.get("starting_balance", 0)),
                monthly_income_mean=float(args.get("monthly_income_mean", 0)),
                monthly_income_std=float(args.get("monthly_income_std") or 0),
                monthly_expense_mean=float(args.get("monthly_expense_mean", 0)),
                monthly_expense_std=float(args.get("monthly_expense_std") or 0),
                months=int(args.get("months") or 12),
                n_sims=int(args.get("n_sims") or 5000),
                seed=int(seed) if seed is not None else None,
                ruin_threshold=float(args.get("ruin_threshold") or 0),
            )
            return json.dumps(result)
        except (TypeError, ValueError) as exc:
            return json.dumps({"error": str(exc)})

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
