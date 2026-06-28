from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

EMBEDDING_DIM = 1024


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped[Account] = relationship("Account", back_populates="transactions")
    embedding: Mapped[Optional[TransactionEmbedding]] = relationship(
        "TransactionEmbedding", back_populates="transaction", uselist=False
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
