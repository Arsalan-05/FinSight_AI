"""add_transaction_embeddings

Revision ID: a1b2c3d4e5f6
Revises: 603770f84793
Create Date: 2026-06-28 18:45:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "603770f84793"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "transaction_embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.String(36),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_transaction_embeddings_transaction_id",
        "transaction_embeddings",
        ["transaction_id"],
    )
    # IVFFlat index for approximate cosine similarity search.
    # lists=100 is a sensible starting point; tune to ~sqrt(row_count) at scale.
    op.execute(
        "CREATE INDEX idx_tx_embeddings_ivfflat "
        "ON transaction_embeddings "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("transaction_embeddings")
