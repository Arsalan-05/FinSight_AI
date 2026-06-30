"""Live stock/ETF quotes — Finnhub (preferred) with Yahoo Finance fallback."""

from __future__ import annotations

import json
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
_FINNHUB_QUOTE = "https://finnhub.io/api/v1/quote?symbol={symbol}&token={token}"
_USER_AGENT = "FinSightAI/1.4 (+https://github.com/Arsalan-05/FinSight_AI)"


def _fetch_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode()))


def _quote_from_finnhub(symbol: str) -> dict[str, Any] | None:
    token = settings.finnhub_api_key.strip()
    if not token:
        return None
    try:
        data = _fetch_json(_FINNHUB_QUOTE.format(symbol=symbol, token=token))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None
    price = data.get("c")
    if price is None or price == 0:
        return None
    prev = float(data.get("pc") or price)
    current = float(price)
    change_pct = round(((current - prev) / prev) * 100, 2) if prev else 0.0
    return {
        "symbol": symbol,
        "price": round(current, 2),
        "currency": "USD",
        "change_pct": change_pct,
        "previous_close": round(prev, 2),
        "source": "finnhub",
        "live": True,
    }


def _quote_from_yahoo(symbol: str) -> dict[str, Any]:
    try:
        payload = _fetch_json(_YAHOO_CHART.format(symbol=symbol))
        results = payload.get("chart", {}).get("result") or []
        if not results:
            return {"error": f"No market data for {symbol}.", "symbol": symbol}
        meta = results[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            return {"error": f"No price available for {symbol}.", "symbol": symbol}
        prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
        current = float(price)
        change_pct = round(((current - prev) / prev) * 100, 2) if prev else 0.0
        return {
            "symbol": symbol,
            "price": round(current, 2),
            "currency": str(meta.get("currency") or "USD"),
            "change_pct": change_pct,
            "previous_close": round(prev, 2),
            "source": "yahoo_finance",
            "live": True,
        }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return {
            "error": f"Market data unavailable for {symbol}: {exc.__class__.__name__}",
            "symbol": symbol,
        }


def get_market_quote(symbol: str) -> dict[str, Any]:
    """Return a live quote for a stock or ETF ticker."""
    key = symbol.upper().strip()
    if not key or len(key) > 12:
        return {"error": "Invalid symbol.", "symbol": symbol}

    finnhub = _quote_from_finnhub(key)
    if finnhub:
        return finnhub
    return _quote_from_yahoo(key)
