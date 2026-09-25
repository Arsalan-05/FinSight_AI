"""Orchestrate all money-leak detectors and persist findings."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List, TypedDict

from sqlalchemy.orm import Session

from db.models import Account, LeakFinding, Transaction
from insights.recurring import detect_recurring_charges
from leaks.boc import get_rate_dict
from leaks.duplicates import detect_duplicates
from leaks.fees import detect_fees
from leaks.fx import detect_fx_markup, findings_from_fx_result
from leaks.subscriptions import detect_forgotten_subscriptions, detect_price_creep


class FindingDict(TypedDict, total=False):
    type: str
    amount_cad: float
    status: str
    title: str
    message: str
    evidence: Dict[str, Any]
    fingerprint: str
    id: str


def _load_transactions(db: Session, user_id: str) -> List[Transaction]:
    account_ids = [
        a.id for a in db.query(Account.id).filter(Account.user_id == user_id).all()
    ]
    if not account_ids:
        return []
    return (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.transaction_date.asc())
        .all()
    )


def scan_all_leaks(db: Session, user_id: str) -> List[FindingDict]:
    """
    Run every detector for `user_id` and return merged FindingDict list.

    Pure merge of detector outputs — does not write to the DB.
    """
    txs = _load_transactions(db, user_id)
    if not txs:
        return []

    account_ids = list({t.account_id for t in txs})
    recurring = detect_recurring_charges(db, account_ids=account_ids)
    # Only exclude merchants with 3+ occurrences — 2-hit clusters are often duplicates.
    recurring_merchants = [
        r["merchant"] for r in recurring if r.get("merchant") and r.get("occurrences", 0) >= 3
    ]
    rates = get_rate_dict(db, prefer_live=False)
    fx_result = detect_fx_markup(txs, rates, year=date.today().year)
    fx_findings = findings_from_fx_result(fx_result)

    dup_findings = detect_duplicates(txs, recurring_merchants=recurring_merchants)
    fee_result = detect_fees(txs, year=date.today().year)
    creep = detect_price_creep(txs)
    forgotten = detect_forgotten_subscriptions(txs)

    merged: List[FindingDict] = []
    for block in (fx_findings, dup_findings, fee_result["findings"], creep, forgotten):
        for item in block:
            merged.append(item)  # type: ignore[arg-type]
    return merged


def upsert_findings(
    db: Session,
    user_id: str,
    findings: List[FindingDict],
) -> List[LeakFinding]:
    """
    Persist findings keyed by fingerprint in evidence_json.

    Preserves dismissed/resolved status; updates amount/evidence for open rows.
    """
    existing = (
        db.query(LeakFinding).filter(LeakFinding.user_id == user_id).all()
    )
    by_fp: Dict[str, LeakFinding] = {}
    for row in existing:
        try:
            ev = json.loads(row.evidence_json or "{}")
        except json.JSONDecodeError:
            ev = {}
        fp = ev.get("fingerprint")
        if fp:
            by_fp[str(fp)] = row

    results: List[LeakFinding] = []
    for finding in findings:
        fp = str(finding.get("fingerprint") or _fallback_fingerprint(finding))
        evidence = dict(finding.get("evidence") or {})
        evidence["fingerprint"] = fp
        evidence["title"] = finding.get("title")
        evidence["message"] = finding.get("message")

        prior = by_fp.get(fp)
        if prior is not None:
            if prior.status in ("dismissed", "resolved"):
                results.append(prior)
                continue
            prior.amount_cad = float(finding.get("amount_cad") or 0)
            prior.type = str(finding.get("type") or prior.type)
            prior.evidence_json = json.dumps(evidence)
            results.append(prior)
            continue

        row = LeakFinding(
            user_id=user_id,
            type=str(finding.get("type") or "unknown"),
            amount_cad=float(finding.get("amount_cad") or 0),
            evidence_json=json.dumps(evidence),
            status=str(finding.get("status") or "open"),
        )
        db.add(row)
        by_fp[fp] = row
        results.append(row)

    db.commit()
    for row in results:
        db.refresh(row)
    return results


def _fallback_fingerprint(finding: FindingDict) -> str:
    ev = finding.get("evidence") or {}
    tx = ev.get("transaction_id") or ev.get("transaction_ids") or ""
    return f"{finding.get('type')}:{tx}:{finding.get('amount_cad')}"


def money_recovered_summary(db: Session, user_id: str) -> Dict[str, Any]:
    """Dashboard card: total found, total resolved, open count."""
    rows = db.query(LeakFinding).filter(LeakFinding.user_id == user_id).all()
    total_found = sum(float(r.amount_cad) for r in rows if r.status != "dismissed")
    total_resolved = sum(float(r.amount_cad) for r in rows if r.status == "resolved")
    open_rows = [r for r in rows if r.status == "open"]
    return {
        "total_found_cad": round(total_found, 2),
        "total_resolved_cad": round(total_resolved, 2),
        "open_count": len(open_rows),
        "open_amount_cad": round(sum(float(r.amount_cad) for r in open_rows), 2),
    }


def finding_to_dict(row: LeakFinding) -> Dict[str, Any]:
    try:
        evidence = json.loads(row.evidence_json or "{}")
    except json.JSONDecodeError:
        evidence = {}
    return {
        "id": row.id,
        "user_id": row.user_id,
        "type": row.type,
        "amount_cad": float(row.amount_cad),
        "evidence": evidence,
        "status": row.status,
        "title": evidence.get("title"),
        "message": evidence.get("message"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
