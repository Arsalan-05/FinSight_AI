"""Monthly category budgets."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependencies import get_db
from app.schemas import BudgetCreate, BudgetOut, BudgetWithSpendOut
from db.models import Account, Budget, Transaction, User

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _budget_with_spend(db: Session, budget: Budget) -> BudgetWithSpendOut:
    today = date.today()
    month_start = date(today.year, today.month, 1)
    spent = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Account.user_id == budget.user_id,
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date <= today,
            Transaction.amount < 0,
            Transaction.category.ilike(budget.category),
        )
        .scalar()
    )
    spent_abs = abs(float(spent or 0))
    limit = float(budget.monthly_limit)
    pct = (spent_abs / limit * 100) if limit > 0 else 0
    return BudgetWithSpendOut(
        id=budget.id,
        category=budget.category,
        monthly_limit=limit,
        created_at=budget.created_at,
        spent_this_month=round(spent_abs, 2),
        percent_used=round(min(pct, 999), 1),
    )


@router.get("/", response_model=list[BudgetWithSpendOut])
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BudgetWithSpendOut]:
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    return [_budget_with_spend(db, b) for b in budgets]


@router.post("/", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Budget:
    budget = Budget(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        category=payload.category.strip(),
        monthly_limit=payload.monthly_limit,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    budget = db.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
