"""Tests for MCP external tools."""

from __future__ import annotations

from unittest.mock import patch

from mcp.currency import convert_currency
from mcp.market import get_market_quote
from mcp.registry import execute_mcp_tool

_YAHOO_FIXTURE = {
    "chart": {
        "result": [
            {
                "meta": {
                    "symbol": "AAPL",
                    "currency": "USD",
                    "regularMarketPrice": 210.5,
                    "chartPreviousClose": 208.0,
                }
            }
        ]
    }
}


def test_convert_currency_usd_to_cad() -> None:
    result = convert_currency(100, "USD", "CAD")
    assert result["from_currency"] == "USD"
    assert result["to_currency"] == "CAD"
    assert result["converted_amount"] > 100


def test_convert_currency_unsupported() -> None:
    result = convert_currency(10, "USD", "JPY")
    assert "error" in result


@patch("mcp.market._fetch_json")
def test_get_market_quote_yahoo(mock_fetch: object) -> None:
    mock_fetch.return_value = _YAHOO_FIXTURE  # type: ignore[attr-defined]
    result = get_market_quote("AAPL")
    assert result["symbol"] == "AAPL"
    assert result["price"] == 210.5
    assert result["live"] is True
    assert result["source"] == "yahoo_finance"


@patch("mcp.market._fetch_json")
def test_execute_mcp_tool_registry(mock_fetch: object) -> None:
    mock_fetch.return_value = {  # type: ignore[attr-defined]
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "MSFT",
                        "currency": "USD",
                        "regularMarketPrice": 425.0,
                        "chartPreviousClose": 420.0,
                    }
                }
            ]
        }
    }
    raw = execute_mcp_tool("get_market_quote", {"symbol": "MSFT"})
    assert "MSFT" in raw
    assert "425" in raw
