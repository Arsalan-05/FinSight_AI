"""Multi-account balance reconciliation insights."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Account, Transaction


def reconcile_accounts(
    db: Session,
    *,
    account_ids: list[str] | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Explain net cash flow across accounts for the period."""
    since = date.today() - timedelta(days=days)
    q = db.query(Transaction).filter(Transaction.transaction_date >= since)
    if account_ids is not None:
        if not account_ids:
            return {
                "period_days": days,
                "accounts": [],
                "net_change": 0,
                "explanation": "No accounts.",
            }
        q = q.filter(Transaction.account_id.in_(account_ids))

    rows = (
        q.with_entities(
            Transaction.account_id,
            func.sum(Transaction.amount).label("net"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.account_id)
        .all()
    )

    account_map: dict[str, Account] = {}
    if account_ids:
        for acc_row in db.query(Account).filter(Account.id.in_(account_ids)).all():
            account_map[acc_row.id] = acc_row

    accounts_out: list[dict[str, Any]] = []
    total_net = 0.0
    for account_id, net, count in rows:
        net_f = float(net or 0)
        total_net += net_f
        acc: Account | None = account_map.get(account_id)
        accounts_out.append(
            {
                "account_id": account_id,
                "name": acc.name if acc else account_id,
                "institution": acc.institution if acc else "",
                "type": acc.account_type if acc else "",
                "net_change": round(net_f, 2),
                "transaction_count": int(count),
            }
        )

    inflow = sum(a["net_change"] for a in accounts_out if a["net_change"] > 0)
    outflow = sum(a["net_change"] for a in accounts_out if a["net_change"] < 0)

    tx_count = sum(a["transaction_count"] for a in accounts_out)
    explanation = (
        f"Over the last {days} days, net change across all accounts is "
        f"${total_net:,.2f} ({len(accounts_out)} accounts, {tx_count} transactions). "
        f"Inflows ${inflow:,.2f}, outflows ${outflow:,.2f}."
    )

    return {
        "period_days": days,
        "accounts": accounts_out,
        "net_change": round(total_net, 2),
        "total_inflow": round(inflow, 2),
        "total_outflow": round(outflow, 2),
        "explanation": explanation,
    }
