from __future__ import annotations

from typing import Any

from mcp.boc_rates import convert_with_boc, get_boc_rates

# Fallback static rates when BoC unavailable
_STATIC_TO_CAD: dict[str, float] = {
    "USD": 1.37,
    "EUR": 1.48,
    "GBP": 1.73,
    "PKR": 0.0049,
    "CAD": 1.0,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
    """Convert between currencies — BoC live rates when possible, static fallback."""
    src = from_currency.upper().strip()
    dst = to_currency.upper().strip()

    # Try BoC for major pairs involving CAD
    if src in {"USD", "EUR", "GBP", "CAD"} and dst in {"USD", "EUR", "GBP", "CAD"}:
        result = convert_with_boc(amount, src, dst)
        if "error" not in result:
            return result

    if src not in _STATIC_TO_CAD or dst not in _STATIC_TO_CAD:
        supported = ", ".join(sorted(_STATIC_TO_CAD))
        return {"error": f"Unsupported currency. Supported: {supported}"}

    cad = float(amount) * _STATIC_TO_CAD[src]
    converted = cad / _STATIC_TO_CAD[dst]
    return {
        "amount": round(float(amount), 2),
        "from_currency": src,
        "to_currency": dst,
        "converted_amount": round(converted, 2),
        "rate_note": "Static fallback rate — BoC unavailable for this pair.",
    }


def get_exchange_rates() -> dict[str, Any]:
    """Return live BoC rates or static fallback."""
    boc = get_boc_rates()
    if "error" not in boc:
        return boc
    return {
        "source": "static_fallback",
        "rates": {f"{k}CAD": v for k, v in _STATIC_TO_CAD.items() if k != "CAD"},
        "note": str(boc.get("error", "")),
    }
