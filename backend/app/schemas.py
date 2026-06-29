from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator

# ── User ──────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    name: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    email: str
    name: str
    created_at: datetime


# ── Account ───────────────────────────────────────────────────────────────────


class AccountCreate(BaseModel):
    user_id: str
    name: str
    institution: str
    account_type: str

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        allowed = {"checking", "savings", "credit"}
        if v not in allowed:
            raise ValueError(f"account_type must be one of {allowed}")
        return v


class AccountOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    name: str
    institution: str
    account_type: str
    created_at: datetime


# ── Transaction ───────────────────────────────────────────────────────────────


class TransactionCreate(BaseModel):
    account_id: str
    transaction_date: date
    description: str
    amount: float
    category: str = "Uncategorized"
    merchant: str | None = None
    notes: str | None = None


class TransactionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    account_id: str
    transaction_date: date
    description: str
    amount: float
    category: str
    merchant: str | None
    notes: str | None
    created_at: datetime


class TransactionListOut(BaseModel):
    total: int
    items: list[TransactionOut]


# ── Chat ──────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None
