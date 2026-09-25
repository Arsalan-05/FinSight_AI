from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

EMBEDDING_DIM = 1024  # Voyage voyage-4-large (default); Ollama nomic-embed-text uses 768


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    auth_id: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    agent_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    alert_prefs_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"spend_alerts": true, "email_digest": false}',
    )
    category_rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    accounts: Mapped[list[Account]] = relationship("Account", back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    # checking | savings | credit
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    plaid_account_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    bank_connection_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bank_connections.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # negative = debit
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="Uncategorized")
    merchant: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plaid_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped[Account] = relationship("Account", back_populates="transactions")
    embedding: Mapped[Optional[TransactionEmbedding]] = relationship(
        "TransactionEmbedding",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="plaid")
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    institution_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    transactions_cursor: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # JSON-serialized LangChain message dicts for conversation history
    messages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    memory_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class TransactionEmbedding(Base):
    __tablename__ = "transaction_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # The text that was embedded — useful for debugging / re-embedding
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transaction: Mapped[Transaction] = relationship("Transaction", back_populates="embedding")


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FxRate(Base):
    """Bank of Canada (or cached) FX rate for a calendar day and pair (e.g. USDCAD)."""

    __tablename__ = "fx_rates"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    pair: Mapped[str] = mapped_column(String(16), primary_key=True)
    rate: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="bank_of_canada")


class LeakFinding(Base):
    """Persisted money-leak finding from deterministic detectors."""

    __tablename__ = "leak_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    # fx_markup | duplicate | fee | subscription_creep | forgotten_subscription
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amount_cad: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # open | dismissed | resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MerchantAlias(Base):
    """Maps noisy POS / processor merchant strings to a canonical name."""

    __tablename__ = "merchant_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="normalize")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Append-only user-visible audit trail (tool calls, exports, deletes)."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvalRun(Base):
    """Optional persisted eval run (file-based results remain primary for now)."""

    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    subset: Mapped[str] = mapped_column(String(50), nullable=False, default="smoke")
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
