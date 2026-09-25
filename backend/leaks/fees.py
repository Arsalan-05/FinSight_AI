"""Bank fee scanner — NSF, overdraft, monthly, e-Transfer, ATM fees."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Ordered most-specific first so NSF beats generic "fee"
_FEE_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "nsf",
        re.compile(
            r"\b(?:nsf|non[\s-]?sufficient\s+funds|insufficient\s+funds)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "overdraft",
        re.compile(r"\b(?:overdraft|od\s+fee|od\s+interest|overdrawn)\b", re.IGNORECASE),
    ),
    (
        "e_transfer_fee",
        re.compile(
            r"\b(?:e[\s-]?transfer|interac)\b.*\bfee\b|\bfee\b.*\b(?:e[\s-]?transfer|interac)\b|"
            r"\binterac\s+(?:e[\s-]?transfer\s+)?fee\b",
            re.IGNORECASE,
        ),
    ),
    (
        "atm_fee",
        re.compile(
            r"\b(?:atm|abm)\b.*\b(?:fee|charge)\b|\b(?:fee|charge)\b.*\b(?:atm|abm)\b|"
            r"\bout[\s-]?of[\s-]?network\s+atm\b",
            re.IGNORECASE,
        ),
    ),
    (
        "monthly_fee",
        re.compile(
            r"\b(?:monthly\s+(?:account\s+)?fee|account\s+fee|service\s+charge|"
            r"monthly\s+service|package\s+fee|chequing\s+fee)\b",
            re.IGNORECASE,
        ),
    ),
]

_FEE_LABELS = {
    "nsf": "NSF fee",
    "overdraft": "Overdraft fee",
    "e_transfer_fee": "E-Transfer fee",
    "atm_fee": "ATM fee",
    "monthly_fee": "Monthly account fee",
}


def classify_fee(description: str, category: str = "") -> Optional[str]:
    """Return fee type key or None if the text is not a known bank fee."""
    blob = f"{description or ''} {category or ''}"
    for fee_type, pattern in _FEE_PATTERNS:
        if pattern.search(blob):
            return fee_type
    return None


def detect_fees(
    transactions: Sequence[Any],
    *,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Classify fee transactions and sum yearly total.

    Returns per-fee findings plus aggregate yearly_total_cad.
    """
    target_year = year or date.today().year
    items: List[Dict[str, Any]] = []
    by_type: Dict[str, float] = {}
    yearly_total = 0.0

    for tx in transactions:
        if float(getattr(tx, "amount", 0) or 0) >= 0:
            continue
        tx_date = getattr(tx, "transaction_date")
        if year is not None and tx_date.year != year:
            continue

        desc = getattr(tx, "description", "") or ""
        cat = getattr(tx, "category", "") or ""
        fee_type = classify_fee(desc, cat)
        if fee_type is None:
            continue

        amount = abs(float(tx.amount))
        label = _FEE_LABELS.get(fee_type, fee_type)
        tx_id = getattr(tx, "id", None)

        items.append(
            {
                "type": "fee",
                "amount_cad": round(amount, 2),
                "status": "open",
                "title": label,
                "message": f"{label}: ${amount:.2f} on {tx_date.isoformat()}.",
                "evidence": {
                    "fee_type": fee_type,
                    "transaction_id": tx_id,
                    "date": tx_date.isoformat(),
                    "description": desc,
                    "category": cat,
                    "amount": round(amount, 2),
                },
                "fingerprint": f"fee:{fee_type}:{tx_id}",
            }
        )
        by_type[fee_type] = round(by_type.get(fee_type, 0.0) + amount, 2)
        if tx_date.year == target_year:
            yearly_total += amount

    yearly_total = round(yearly_total, 2)
    findings = list(items)
    if yearly_total > 0:
        findings.append(
            {
                "type": "fee",
                "amount_cad": yearly_total,
                "status": "open",
                "title": f"Bank fees total ({target_year})",
                "message": f"You've paid ${yearly_total:.2f} in bank fees this year.",
                "evidence": {
                    "kind": "yearly_summary",
                    "year": target_year,
                    "by_type": by_type,
                    "transaction_ids": [i["evidence"]["transaction_id"] for i in items],
                    "count": len(items),
                },
                "fingerprint": f"fee_yearly:{target_year}",
            }
        )

    return {
        "items": items,
        "findings": findings,
        "yearly_total_cad": yearly_total,
        "by_type": by_type,
        "year": target_year,
    }
