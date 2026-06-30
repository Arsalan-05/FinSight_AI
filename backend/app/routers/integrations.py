"""Plaid bank connections — link token, exchange, sync."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependencies import get_db
from app.schemas import (
    BankConnectionOut,
    PlaidExchangeIn,
    PlaidLinkTokenOut,
    PlaidStatusOut,
    PlaidSyncResultOut,
)
from db.models import BankConnection, User
from integrations.plaid_client import (
    create_link_token,
    exchange_public_token,
    get_item,
    plaid_configured,
)
from integrations.plaid_sync import sync_connection

router = APIRouter(prefix="/integrations/plaid", tags=["integrations"])


@router.get("/status", response_model=PlaidStatusOut)
def plaid_status() -> PlaidStatusOut:
    from app.config import settings

    return PlaidStatusOut(
        enabled=plaid_configured(),
        environment=settings.plaid_env if plaid_configured() else None,
    )


@router.post("/link-token", response_model=PlaidLinkTokenOut)
def plaid_link_token(
    current_user: User = Depends(get_current_user),
) -> PlaidLinkTokenOut:
    if not plaid_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid is not configured. Add PLAID_CLIENT_ID and PLAID_SECRET to .env.",
        )
    try:
        data = create_link_token(user_id=current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PlaidLinkTokenOut(link_token=data["link_token"], expiration=data.get("expiration", ""))


@router.post("/exchange", response_model=BankConnectionOut)
def plaid_exchange(
    payload: PlaidExchangeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BankConnection:
    if not plaid_configured():
        raise HTTPException(status_code=503, detail="Plaid not configured")
    try:
        exchanged = exchange_public_token(payload.public_token)
        access_token = exchanged["access_token"]
        item_id = exchanged["item_id"]
        item = get_item(access_token)
        institution = (item.get("item") or {}).get("institution_id") or ""
        institution_name = payload.institution_name or institution or "Linked bank"
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    existing = (
        db.query(BankConnection)
        .filter(
            BankConnection.user_id == current_user.id,
            BankConnection.item_id == item_id,
        )
        .first()
    )
    if existing:
        conn = existing
        conn.access_token = access_token
        conn.status = "active"
    else:
        conn = BankConnection(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            item_id=item_id,
            access_token=access_token,
            institution_name=institution_name,
            institution_id=institution or None,
        )
        db.add(conn)
    db.commit()
    db.refresh(conn)

    try:
        sync_connection(db, conn)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Bank linked but initial sync failed: {exc}",
        ) from exc

    db.refresh(conn)
    return conn


@router.get("/connections", response_model=list[BankConnectionOut])
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BankConnection]:
    return (
        db.query(BankConnection)
        .filter(BankConnection.user_id == current_user.id, BankConnection.status == "active")
        .order_by(BankConnection.created_at.desc())
        .all()
    )


@router.post("/sync", response_model=list[PlaidSyncResultOut])
def sync_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    connections = (
        db.query(BankConnection)
        .filter(BankConnection.user_id == current_user.id, BankConnection.status == "active")
        .all()
    )
    if not connections:
        return []
    results: list[dict] = []
    for conn in connections:
        try:
            results.append(sync_connection(db, conn))
        except RuntimeError as exc:
            results.append(
                {
                    "connection_id": conn.id,
                    "institution": conn.institution_name,
                    "error": str(exc),
                }
            )
    return results


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    conn = db.get(BankConnection, connection_id)
    if not conn or conn.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn.status = "disconnected"
    db.commit()
