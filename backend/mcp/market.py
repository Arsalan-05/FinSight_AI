from __future__ import annotations

from typing import Any

# Static demo quotes — replace with live market data API in production.
_DEMO_QUOTES: dict[str, dict[str, Any]] = {
    "AAPL": {"symbol": "AAPL", "price": 198.42, "currency": "USD", "change_pct": 0.84},
    "MSFT": {"symbol": "MSFT", "price": 425.10, "currency": "USD", "change_pct": -0.32},
    "GOOGL": {"symbol": "GOOGL", "price": 176.55, "currency": "USD", "change_pct": 1.12},
    "TSLA": {"symbol": "TSLA", "price": 248.30, "currency": "USD", "change_pct": -1.45},
    "SPY": {"symbol": "SPY", "price": 542.18, "currency": "USD", "change_pct": 0.21},
}


def get_market_quote(symbol: str) -> dict[str, Any]:
    """Return a static demo quote for a stock/ETF symbol."""
    key = symbol.upper().strip()
    if key not in _DEMO_QUOTES:
        return {
            "error": f"No demo quote for {key}.",
            "available_symbols": sorted(_DEMO_QUOTES),
        }
    quote = dict(_DEMO_QUOTES[key])
    quote["note"] = "Static demo data for development only."
    return quote
