"""FX markup detector — implied bank rate vs Bank of Canada official rate."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from leaks.boc import RateDict, nearest_rate

# Matches "USD 49.99", "49.99 USD", "EUR 12.00", "$49.99 USD", etc.
_FOREIGN_AMOUNT_RE = re.compile(
    r"(?:"
    r"(?P<code1>USD|EUR|GBP|AUD|JPY|CHF|MXN|CNY)\s*\$?\s*(?P<amt1>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"|"
    r"\$?\s*(?P<amt2>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<code2>USD|EUR|GBP|AUD|JPY|CHF|MXN|CNY)"
    r")",
    re.IGNORECASE,
)

# Soft signal that a description mentions foreign currency without a parseable amount
_FOREIGN_HINT_RE = re.compile(
    r"\b(?:USD|EUR|GBP|AUD|JPY|CHF|MXN|CNY|foreign\s*ex(?:change)?|fx\s*purchase)\b",
    re.IGNORECASE,
)

TxLike = Any  # Transaction ORM or duck-typed object with amount/date/description


def parse_foreign_amount(description: str) -> Optional[Tuple[str, float]]:
    """Extract (currency_code, foreign_amount) from a transaction description."""
    if not description:
        return None
    m = _FOREIGN_AMOUNT_RE.search(description)
    if not m:
        return None
    code = (m.group("code1") or m.group("code2") or "").upper()
    raw = m.group("amt1") or m.group("amt2") or ""
    try:
        amount = float(raw.replace(",", ""))
    except ValueError:
        return None
    if amount <= 0:
        return None
    return code, amount


def _pair_for(currency: str) -> str:
    return f"{currency.upper()}CAD"


def detect_fx_markup(
    transactions: Sequence[TxLike],
    boc_rates: RateDict,
    *,
    year: Optional[int] = None,
    min_markup_cad: float = 0.25,
    min_markup_pct: float = 0.5,
) -> Dict[str, Any]:
    """
    Compare implied FX rate (CAD ÷ foreign) to BoC rates.

    Returns per-transaction findings plus yearly markup total.
    Transactions with foreign-currency hints but no parseable amount are
    flagged as unverifiable (amount_cad=0, not counted in yearly total).
    """
    items: List[Dict[str, Any]] = []
    unverifiable: List[Dict[str, Any]] = []
    yearly_total = 0.0
    target_year = year or date.today().year

    for tx in transactions:
        desc = getattr(tx, "description", "") or ""
        cad = abs(float(getattr(tx, "amount", 0) or 0))
        tx_date: date = getattr(tx, "transaction_date")
        tx_id = getattr(tx, "id", None)

        if year is not None and tx_date.year != year:
            continue
        if float(getattr(tx, "amount", 0) or 0) >= 0:
            continue  # credits / refunds

        parsed = parse_foreign_amount(desc)
        if parsed is None:
            if _FOREIGN_HINT_RE.search(desc):
                unverifiable.append(
                    {
                        "type": "fx_markup",
                        "amount_cad": 0.0,
                        "status": "open",
                        "title": "Unverifiable FX purchase",
                        "message": (
                            "Foreign currency mentioned but amount missing — "
                            "cannot compute markup."
                        ),
                        "evidence": {
                            "transaction_id": tx_id,
                            "date": tx_date.isoformat(),
                            "description": desc,
                            "cad_amount": round(cad, 2),
                            "unverifiable": True,
                            "reason": "foreign_amount_missing",
                        },
                        "fingerprint": f"fx_unverifiable:{tx_id}",
                    }
                )
            continue

        currency, foreign_amt = parsed
        if currency == "CAD":
            continue

        pair = _pair_for(currency)
        boc = nearest_rate(boc_rates, tx_date, pair)
        if boc is None or boc <= 0:
            unverifiable.append(
                {
                    "type": "fx_markup",
                    "amount_cad": 0.0,
                    "status": "open",
                    "title": f"Missing BoC rate for {pair}",
                    "message": f"No BoC rate for {pair} near {tx_date.isoformat()}.",
                    "evidence": {
                        "transaction_id": tx_id,
                        "date": tx_date.isoformat(),
                        "description": desc,
                        "foreign_currency": currency,
                        "foreign_amount": foreign_amt,
                        "cad_amount": round(cad, 2),
                        "pair": pair,
                        "unverifiable": True,
                        "reason": "boc_rate_missing",
                    },
                    "fingerprint": f"fx_no_rate:{tx_id}",
                }
            )
            continue

        implied = cad / foreign_amt
        markup_cad = cad - (foreign_amt * boc)
        markup_pct = ((implied - boc) / boc) * 100.0

        if markup_cad < min_markup_cad and abs(markup_pct) < min_markup_pct:
            continue
        if markup_cad <= 0:
            continue  # bank beat BoC — not a leak

        finding = {
            "type": "fx_markup",
            "amount_cad": round(markup_cad, 2),
            "status": "open",
            "title": f"FX markup on {currency} purchase",
            "message": (
                f"Implied {implied:.4f} vs BoC {boc:.4f} ({pair}) — "
                f"${markup_cad:.2f} markup ({markup_pct:.1f}%)."
            ),
            "evidence": {
                "transaction_id": tx_id,
                "date": tx_date.isoformat(),
                "description": desc,
                "foreign_currency": currency,
                "foreign_amount": foreign_amt,
                "cad_amount": round(cad, 2),
                "pair": pair,
                "implied_rate": round(implied, 6),
                "boc_rate": round(boc, 6),
                "markup_pct": round(markup_pct, 2),
                "unverifiable": False,
            },
            "fingerprint": f"fx_markup:{tx_id}",
        }
        items.append(finding)
        if tx_date.year == target_year:
            yearly_total += markup_cad

    yearly_total = round(yearly_total, 2)
    return {
        "items": items,
        "unverifiable": unverifiable,
        "yearly_total_cad": yearly_total,
        "year": target_year,
        "no_fx_fee_card_savings_cad": yearly_total,
    }


def findings_from_fx_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten detector output into FindingDict list (including unverifiable)."""
    out: List[Dict[str, Any]] = list(result.get("items") or [])
    out.extend(result.get("unverifiable") or [])
    # Attach summary finding when there is a yearly total
    yearly = float(result.get("yearly_total_cad") or 0)
    if yearly > 0 and result.get("items"):
        out.append(
            {
                "type": "fx_markup",
                "amount_cad": yearly,
                "status": "open",
                "title": f"FX markup total ({result.get('year')})",
                "message": (
                    f"You're losing ~${yearly:.2f}/year to FX markup. "
                    f"A no-FX-fee card would have saved ${yearly:.2f}."
                ),
                "evidence": {
                    "kind": "yearly_summary",
                    "year": result.get("year"),
                    "transaction_ids": [
                        i["evidence"]["transaction_id"] for i in result["items"]
                    ],
                    "per_tx_count": len(result["items"]),
                    "no_fx_fee_card_savings_cad": yearly,
                },
                "fingerprint": f"fx_yearly:{result.get('year')}",
            }
        )
    return out
