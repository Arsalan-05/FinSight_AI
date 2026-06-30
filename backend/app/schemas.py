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
    plaid_linked: bool = False
    last_synced_at: datetime | None = None


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


class TransactionUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    merchant: str | None = None
    notes: str | None = None


# ── Chat ──────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None


# ── Plaid / bank connections ──────────────────────────────────────────────────


class PlaidStatusOut(BaseModel):
    enabled: bool
    environment: str | None = None


class PlaidLinkTokenOut(BaseModel):
    link_token: str
    expiration: str = ""


class PlaidExchangeIn(BaseModel):
    public_token: str
    institution_name: str | None = None


class BankConnectionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    institution_name: str
    institution_id: str | None
    status: str
    last_synced_at: datetime | None
    created_at: datetime


class BootstrapOut(BaseModel):
    user_id: str
    email: str
    name: str
    provisioned_demo: bool
    db_connected: bool
    db_host: str
    using_fallback: bool
    db_error: str | None = None
    account_count: int
    transaction_count: int


class PlaidSyncResultOut(BaseModel):
    connection_id: str
    institution: str
    added: int | None = None
    modified: int | None = None
    removed: int | None = None
    modified_seen: int | None = None
    last_synced_at: str | None = None
    error: str | None = None


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float


class BudgetOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    category: str
    monthly_limit: float
    created_at: datetime


class BudgetWithSpendOut(BudgetOut):
    spent_this_month: float = 0
    percent_used: float = 0


class NotificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    kind: str
    severity: str
    title: str
    body: str
    read: bool
    created_at: datetime


class AlertPreferencesIn(BaseModel):
    spend_alerts: bool | None = None
    email_digest: bool | None = None


class AlertPreferencesOut(BaseModel):
    spend_alerts: bool = True
    email_digest: bool = False
