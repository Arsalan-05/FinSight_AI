from __future__ import annotations

import csv
import io
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.schemas import TransactionCreate, TransactionListOut, TransactionOut
from db.models import Account, Transaction, TransactionEmbedding
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
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)) -> Transaction:
    if not db.query(Account).filter(Account.id == payload.account_id).first():
        raise HTTPException(status_code=404, detail="Account not found")
    tx = Transaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    _embed_and_store([tx], db)
    return tx


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile,
    account_id: str = Query(..., description="Account to attach transactions to"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """
    Upload a CSV with columns:
      date, description, amount, category (opt), merchant (opt), notes (opt)
    """
    if not db.query(Account).filter(Account.id == account_id).first():
        raise HTTPException(status_code=404, detail="Account not found")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"date", "description", "amount"}
    if reader.fieldnames is None or not required.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=422,
            detail=f"CSV must contain columns: {required}",
        )

    created = 0
    errors: list[str] = []
    created_txs: list[Transaction] = []

    for i, row in enumerate(reader, start=2):
        try:
            tx = Transaction(
                account_id=account_id,
                transaction_date=date.fromisoformat(row["date"].strip()),
                description=row["description"].strip(),
                amount=float(row["amount"].strip()),
                category=row.get("category", "Uncategorized").strip() or "Uncategorized",
                merchant=row.get("merchant", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
            )
            db.add(tx)
            created_txs.append(tx)
            created += 1
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    db.commit()
    _embed_and_store(created_txs, db)
    return {"created": created, "errors": errors}


@router.get("/", response_model=TransactionListOut)
def list_transactions(
    account_id: str | None = Query(None),
    category: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TransactionListOut:
    q = db.query(Transaction)
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
def get_transaction(transaction_id: str, db: Session = Depends(get_db)) -> Transaction:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: str, db: Session = Depends(get_db)) -> None:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
