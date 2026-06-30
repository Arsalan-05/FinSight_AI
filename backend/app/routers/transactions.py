from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.config import settings
from app.dependencies import get_db
from app.schemas import TransactionCreate, TransactionListOut, TransactionOut, TransactionUpdate
from app.scoping import assert_account_owned, scope_transactions
from db.models import Transaction, TransactionEmbedding, User
from ingest.bank_csv import detect_and_parse_csv, guess_merchant
from ingest.interac import normalize_interac_transaction
from rag.embedder import build_content, embed_texts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _embed_and_store(txs: list[Transaction], db: Session) -> None:
    """Embed transactions and persist to transaction_embeddings.

    Uses Ollama (free) or Voyage AI depending on EMBEDDING_PROVIDER.
    Silently skips if embeddings are unavailable or the call fails.
    """
    if not settings.embeddings_configured:
        return
    try:
        contents = [build_content(tx) for tx in txs]
        vectors = embed_texts(contents, input_type="document")
        for tx, content, vector in zip(txs, contents, vectors):
            db.add(
                TransactionEmbedding(
                    transaction_id=tx.id,
                    content=content,
                    embedding=vector,
                )
            )
        db.commit()
    except Exception:
        logger.exception("Embedding failed — transactions saved without embeddings")
        db.rollback()


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Transaction:
    try:
        assert_account_owned(db, payload.account_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    tx = Transaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    _embed_and_store([tx], db)
    if current_user:
        from notifications.alerts import check_budget_alerts

        check_budget_alerts(db, current_user)
    return tx


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile,
    account_id: str = Query(..., description="Account to attach transactions to"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    """
    Upload a CSV with columns:
      date, description, amount, category (opt), merchant (opt), notes (opt)
    """
    try:
        assert_account_owned(db, account_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    content = await file.read()
    text = content.decode("utf-8-sig")
    bank, rows, parse_errors = detect_and_parse_csv(text)

    if bank == "unknown" and not rows:
        raise HTTPException(
            status_code=422,
            detail=parse_errors[0] if parse_errors else "Unrecognized CSV format",
        )

    created = 0
    errors: list[str] = list(parse_errors)
    created_txs: list[Transaction] = []

    for i, row in enumerate(rows, start=2):
        try:
            desc, cat, merchant, notes = normalize_interac_transaction(
                row["description"],
                category=row.get("category", "Uncategorized"),
                merchant=row.get("merchant"),
                notes=row.get("notes"),
            )
            if not merchant:
                merchant = guess_merchant(desc)
            tx = Transaction(
                account_id=account_id,
                transaction_date=row["date"],
                description=desc,
                amount=float(row["amount"]),
                category=cat,
                merchant=merchant,
                notes=notes,
            )
            db.add(tx)
            created_txs.append(tx)
            created += 1
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    db.commit()
    _embed_and_store(created_txs, db)
    return {"created": created, "errors": errors, "bank_detected": bank}


@router.get("/", response_model=TransactionListOut)
def list_transactions(
    account_id: str | None = Query(None),
    category: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> TransactionListOut:
    q = scope_transactions(db.query(Transaction), db, current_user)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category:
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    if date_from:
        q = q.filter(Transaction.transaction_date >= date_from)
    if date_to:
        q = q.filter(Transaction.transaction_date <= date_to)

    total = q.count()
    items = q.order_by(Transaction.transaction_date.desc()).offset(offset).limit(limit).all()
    return TransactionListOut(total=total, items=items)  # type: ignore[arg-type]


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Transaction:
    q = scope_transactions(db.query(Transaction), db, current_user)
    tx = q.filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Transaction:
    q = scope_transactions(db.query(Transaction), db, current_user)
    tx = q.filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return tx
    for key, value in data.items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    _embed_and_store([tx], db)
    if current_user:
        from notifications.alerts import check_budget_alerts

        check_budget_alerts(db, current_user)
    return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> None:
    q = scope_transactions(db.query(Transaction), db, current_user)
    tx = q.filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
