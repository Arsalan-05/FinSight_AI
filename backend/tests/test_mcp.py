"""Tests for MCP external tool stubs."""

from __future__ import annotations

from mcp.currency import convert_currency
from mcp.market import get_market_quote
from mcp.registry import execute_mcp_tool


def test_convert_currency_usd_to_cad() -> None:
    result = convert_currency(100, "USD", "CAD")
    assert result["from_currency"] == "USD"
    assert result["to_currency"] == "CAD"
    assert result["converted_amount"] > 100


def test_convert_currency_unsupported() -> None:
    result = convert_currency(10, "USD", "JPY")
    assert "error" in result


def test_get_market_quote() -> None:
    result = get_market_quote("AAPL")
    assert result["symbol"] == "AAPL"
    assert "price" in result


def test_execute_mcp_tool_registry() -> None:
    raw = execute_mcp_tool("get_market_quote", {"symbol": "MSFT"})
    assert "MSFT" in raw
