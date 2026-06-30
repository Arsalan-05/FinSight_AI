from __future__ import annotations

import json
from typing import Any, Callable

from mcp.currency import convert_currency, get_exchange_rates
from mcp.market import get_market_quote

MCP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "convert_currency",
        "description": "Convert an amount between currencies (USD, CAD, EUR, GBP, PKR).",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount to convert."},
                "from_currency": {"type": "string", "description": "Source currency code."},
                "to_currency": {"type": "string", "description": "Target currency code."},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    {
        "name": "get_exchange_rates",
        "description": "Get live USD/CAD, EUR/CAD, GBP/CAD from Bank of Canada.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_market_quote",
        "description": "Get a live stock/ETF quote (e.g. AAPL, MSFT, SPY, TSX:SHOP).",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. AAPL."},
            },
            "required": ["symbol"],
        },
    },
]

_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "convert_currency": convert_currency,
    "get_exchange_rates": get_exchange_rates,
    "get_market_quote": get_market_quote,
}


def execute_mcp_tool(name: str, args: dict[str, Any]) -> str:
    handler = _HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown MCP tool: {name}"})
    if name == "convert_currency":
        result = handler(
            float(args.get("amount", 0)),
            str(args.get("from_currency", "USD")),
            str(args.get("to_currency", "USD")),
        )
    elif name == "get_exchange_rates":
        result = handler()
    else:
        result = handler(str(args.get("symbol", "")))
    return json.dumps(result)


def register_mcp_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for agent registration at startup."""
    return list(MCP_TOOL_DEFINITIONS)
