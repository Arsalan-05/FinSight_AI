"""Money-leak findings API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependencies import get_db
from app.schemas import LeakDraftOut, LeakDraftRequest, LeakFindingOut, LeakUpdate
from db.models import LeakFinding, User
from leaks.drafts import build_draft
from leaks.service import (
    finding_to_dict,
    money_recovered_summary,
    scan_all_leaks,
    upsert_findings,
)

router = APIRouter(prefix="/leaks", tags=["leaks"])


def _owned_finding(db: Session, leak_id: str, user: User) -> LeakFinding:
    row = db.get(LeakFinding, leak_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Leak finding not found")
    return row


@router.get("/", response_model=list[LeakFindingOut])
def list_leaks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rescan: bool = Query(True, description="Re-run detectors before listing"),
) -> list[dict[str, Any]]:
    """List leak findings for the current user (optionally rescanning)."""
    if rescan:
        findings = scan_all_leaks(db, current_user.id)
        upsert_findings(db, current_user.id, findings)

    rows = (
        db.query(LeakFinding)
        .filter(LeakFinding.user_id == current_user.id)
        .order_by(LeakFinding.created_at.desc())
        .all()
    )
    return [finding_to_dict(r) for r in rows]


@router.get("/summary")
def leaks_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Money Recovered card: total found / resolved / open."""
    return money_recovered_summary(db, current_user.id)


@router.patch("/{leak_id}", response_model=LeakFindingOut)
def update_leak(
    leak_id: str,
    payload: LeakUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Dismiss or resolve a finding (or set still_using on forgotten subs)."""
    row = _owned_finding(db, leak_id, current_user)
    if payload.status is not None:
        allowed = {"open", "dismissed", "resolved"}
        if payload.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be one of {sorted(allowed)}",
            )
        row.status = payload.status

    if payload.still_using is not None:
        try:
            evidence = json.loads(row.evidence_json or "{}")
        except json.JSONDecodeError:
            evidence = {}
        evidence["still_using"] = payload.still_using
        row.evidence_json = json.dumps(evidence)
        if payload.still_using is True and row.type == "forgotten_subscription":
            row.status = "dismissed"

    db.commit()
    db.refresh(row)
    return finding_to_dict(row)


@router.post("/{leak_id}/draft", response_model=LeakDraftOut)
def draft_leak_action(
    leak_id: str,
    payload: LeakDraftRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a cancellation / dispute / fee-reversal draft from evidence."""
    row = _owned_finding(db, leak_id, current_user)
    try:
        evidence = json.loads(row.evidence_json or "{}")
    except json.JSONDecodeError:
        evidence = {}

    body = payload or LeakDraftRequest()
    try:
        draft = build_draft(
            row.type,
            evidence,
            kind=body.kind,
            user_name=current_user.name,
            account_email=current_user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return draft
