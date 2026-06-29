from __future__ import annotations

from typing import Any

# Static demo rates — replace with live API in production.
_RATES_TO_USD: dict[str, float] = {
    "USD": 1.0,
    "CAD": 0.73,
    "EUR": 1.08,
    "GBP": 1.27,
    "PKR": 0.0036,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
    """Convert an amount between currencies using static demo rates."""
    src = from_currency.upper().strip()
    dst = to_currency.upper().strip()
    if src not in _RATES_TO_USD or dst not in _RATES_TO_USD:
        supported = ", ".join(sorted(_RATES_TO_USD))
        return {"error": f"Unsupported currency. Supported: {supported}"}
    usd = float(amount) * _RATES_TO_USD[src]
    converted = usd / _RATES_TO_USD[dst]
    return {
        "amount": round(float(amount), 2),
        "from_currency": src,
        "to_currency": dst,
        "converted_amount": round(converted, 2),
        "rate_note": "Static demo rates for development only.",
    }
