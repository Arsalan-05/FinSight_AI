"""Bank of Canada Valet API — live FX rates."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

_BOC_URL = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD,FXEURCAD,FXGBPCAD/json"


def get_boc_rates() -> dict[str, Any]:
    """Fetch latest USD/CAD, EUR/CAD, GBP/CAD from Bank of Canada."""
    try:
        with urlopen(_BOC_URL, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"error": f"BoC API unavailable: {exc}", "source": "bank_of_canada"}

    observations = data.get("observations", [])
    if not observations:
        return {"error": "No observations returned", "source": "bank_of_canada"}

    latest = observations[-1]
    rates: dict[str, float] = {}
    for key, val in latest.items():
        if key.startswith("FX") and isinstance(val, dict) and "v" in val:
            pair = key.replace("FX", "")
            rates[pair] = float(val["v"])

    return {
        "source": "bank_of_canada",
        "date": latest.get("d", ""),
        "rates": rates,
        "note": "Official Bank of Canada daily rates.",
    }


def convert_with_boc(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
    """Convert using BoC rates (CAD-centric pairs)."""
    src = from_currency.upper().strip()
    dst = to_currency.upper().strip()
    boc = get_boc_rates()
    if "error" in boc:
        return boc

    rates: dict[str, float] = boc.get("rates", {})

    # rates are XXXCAD (units of CAD per 1 unit of foreign)
    def to_cad(cur: str, amt: float) -> float | None:
        if cur == "CAD":
            return amt
        pair = f"{cur}CAD"
        if pair in rates:
            return amt * rates[pair]
        inv = f"CAD{cur}"
        if inv in rates and rates[inv] != 0:
            return amt / rates[inv]
        return None

    cad_val = to_cad(src, float(amount))
    if cad_val is None:
        return {"error": f"No BoC rate for {src}", "supported": list(rates.keys())}

    if dst == "CAD":
        converted = cad_val
    else:
        dst_cad = to_cad(dst, 1.0)
        if dst_cad is None or dst_cad == 0:
            return {"error": f"No BoC rate for {dst}"}
        converted = cad_val / dst_cad

    return {
        "amount": round(float(amount), 2),
        "from_currency": src,
        "to_currency": dst,
        "converted_amount": round(converted, 2),
        "rate_date": boc.get("date"),
        "source": "bank_of_canada",
    }
