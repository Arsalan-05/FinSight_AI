from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.dependencies import get_db
from app.schemas import AccountCreate, AccountOut
from app.scoping import accounts_for_user
from db.models import Account, User

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Account:
    owner_id = current_user.id if current_user else payload.user_id
    if not db.query(User).filter(User.id == owner_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump()
    data["user_id"] = owner_id
    account = Account(**data)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[Account]:
    return accounts_for_user(db, current_user)


@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if current_user and account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/by-user/{user_id}", response_model=list[AccountOut])
def list_accounts_for_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[Account]:
    if current_user and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db.query(Account).filter(Account.user_id == user_id).all()
