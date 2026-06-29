"""replace IVFFlat with HNSW index for embedding retrieval

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-29

"""

from __future__ import annotations

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tx_embeddings_hnsw "
        "ON transaction_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_hnsw")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tx_embeddings_ivfflat "
        "ON transaction_embeddings "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
