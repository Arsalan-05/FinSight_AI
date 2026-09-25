"""Subscription price creep and forgotten-subscription detectors."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

def _merchant_key(tx: Any) -> str:
    merchant = (getattr(tx, "merchant", None) or "").strip().lower()
    if len(merchant) >= 3:
        return merchant
    desc = (getattr(tx, "description", "") or "").strip().lower()
    return desc[:40]


def _display(tx: Any) -> str:
    return (getattr(tx, "merchant", None) or getattr(tx, "description", "")[:40] or "Unknown").strip()


def _group_recurring(
    transactions: Sequence[Any],
    *,
    min_occurrences: int = 2,
    amount_tolerance: float = 0.20,
) -> Dict[str, List[Any]]:
    """Bucket debit txs by merchant; keep those that look recurring (similar amounts)."""
    buckets: Dict[str, List[Any]] = defaultdict(list)
    for tx in transactions:
        if float(getattr(tx, "amount", 0) or 0) >= 0:
            continue
        key = _merchant_key(tx)
        if len(key) < 3:
            continue
        buckets[key].append(tx)

    recurring: Dict[str, List[Any]] = {}
    for key, group in buckets.items():
        if len(group) < min_occurrences:
            continue
        amounts = [abs(float(t.amount)) for t in group]
        avg = sum(amounts) / len(amounts)
        # Allow price creep — wider band than insights.recurring (15%)
        if avg > 0 and (max(amounts) - min(amounts)) > avg * max(amount_tolerance, 0.5):
            # Still treat as recurring if gaps look monthly-ish
            dates = sorted(t.transaction_date for t in group)
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            if not gaps or not (20 <= (sum(gaps) / len(gaps)) <= 45):
                continue
        recurring[key] = sorted(group, key=lambda t: t.transaction_date)
    return recurring


def detect_price_creep(
    transactions: Sequence[Any],
    *,
    min_increase_cad: float = 0.50,
) -> List[Dict[str, Any]]:
    """
    Alert when a recurring merchant's charge amount increases over time.

    Example message: "+$2.00/mo since March."
    """
    findings: List[Dict[str, Any]] = []
    for key, group in _group_recurring(transactions).items():
        # Chronological unique amounts (collapse same-day duplicates)
        series: List[Tuple[date, float, Any]] = []
        for tx in group:
            amt = round(abs(float(tx.amount)), 2)
            series.append((tx.transaction_date, amt, tx))

        # Walk for first sustained increase
        first_amt = series[0][1]
        last_amt = series[-1][1]
        if last_amt - first_amt < min_increase_cad:
            # Also check stepwise: any earlier amount lower than later
            stepped = False
            for i in range(1, len(series)):
                if series[i][1] - series[i - 1][1] >= min_increase_cad:
                    stepped = True
                    break
            if not stepped:
                continue

        # Find first date where amount rose above the initial price
        baseline = series[0][1]
        creep_from: Optional[date] = None
        for d, amt, _ in series[1:]:
            if amt - baseline >= min_increase_cad:
                creep_from = d
                break
        if creep_from is None and last_amt - first_amt < min_increase_cad:
            continue
        if creep_from is None:
            creep_from = series[-1][0]

        increase = round(last_amt - first_amt, 2)
        if increase < min_increase_cad:
            # Use max stepwise increase
            increase = round(
                max(series[i][1] - series[i - 1][1] for i in range(1, len(series))),
                2,
            )
            if increase < min_increase_cad:
                continue

        merchant = _display(group[-1])
        month_name = creep_from.strftime("%B")
        findings.append(
            {
                "type": "subscription_creep",
                "amount_cad": increase,
                "status": "open",
                "title": f"Price increase: {merchant}",
                "message": f"+${increase:.2f}/mo since {month_name}.",
                "evidence": {
                    "merchant": merchant,
                    "merchant_key": key,
                    "baseline_amount": first_amt,
                    "current_amount": last_amt,
                    "increase_cad": increase,
                    "since": creep_from.isoformat(),
                    "since_month": month_name,
                    "transaction_ids": [getattr(t, "id", None) for t in group],
                    "amounts": [round(abs(float(t.amount)), 2) for t in group],
                    "dates": [t.transaction_date.isoformat() for t in group],
                },
                "fingerprint": f"creep:{key}",
            }
        )
    return findings


def detect_forgotten_subscriptions(
    transactions: Sequence[Any],
    *,
    lookback_days: int = 180,
    related_activity_window_days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Recurring charges with no related non-subscription activity heuristic.

    "Related activity" = other debit txs whose description/merchant shares a
    significant token with the subscription merchant (beyond the recurring
    charge itself), within recent window.
    """
    since = date.today() - timedelta(days=lookback_days)
    recent = [
        tx
        for tx in transactions
        if getattr(tx, "transaction_date") >= since
        and float(getattr(tx, "amount", 0) or 0) < 0
    ]
    recurring = _group_recurring(recent, min_occurrences=2, amount_tolerance=0.15)
    findings: List[Dict[str, Any]] = []

    # Index all txs for related-activity scan
    all_debits = [
        tx for tx in transactions if float(getattr(tx, "amount", 0) or 0) < 0
    ]

    for key, group in recurring.items():
        tokens = _tokens(key)
        if not tokens:
            continue
        recurring_ids: Set[Any] = {getattr(t, "id", None) for t in group}
        latest = group[-1]
        window_start = date.today() - timedelta(days=related_activity_window_days)

        related = 0
        for tx in all_debits:
            tid = getattr(tx, "id", None)
            if tid in recurring_ids:
                continue
            if getattr(tx, "transaction_date") < window_start:
                continue
            blob = _merchant_key(tx) + " " + (getattr(tx, "description", "") or "").lower()
            # Related if shares a distinctive token but is not the same merchant key
            if _merchant_key(tx) == key:
                continue
            if any(tok in blob for tok in tokens if len(tok) >= 4):
                related += 1

        if related > 0:
            continue  # still "using" the service in some form

        amt = round(abs(float(latest.amount)), 2)
        merchant = _display(latest)
        findings.append(
            {
                "type": "forgotten_subscription",
                "amount_cad": amt,
                "status": "open",
                "title": f"Still using {merchant}?",
                "message": (
                    f"${amt:.2f} recurring with no related activity in the last "
                    f"{related_activity_window_days} days."
                ),
                "evidence": {
                    "merchant": merchant,
                    "merchant_key": key,
                    "amount": amt,
                    "occurrences": len(group),
                    "last_date": latest.transaction_date.isoformat(),
                    "related_activity_count": 0,
                    "still_using": None,  # user toggle placeholder
                    "transaction_ids": [getattr(t, "id", None) for t in group],
                },
                "fingerprint": f"forgotten:{key}",
            }
        )
    return findings


def _tokens(merchant_key: str) -> List[str]:
    stop = {
        "the",
        "and",
        "inc",
        "ltd",
        "llc",
        "com",
        "www",
        "payment",
        "premium",
        "subscription",
        "monthly",
    }
    raw = [t for t in re.split(r"[^a-z0-9]+", merchant_key.lower()) if t]
    return [t for t in raw if t not in stop and len(t) >= 3]
