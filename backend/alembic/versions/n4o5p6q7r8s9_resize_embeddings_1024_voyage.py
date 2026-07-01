"""resize_embeddings_1024_for_voyage

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-07-01

Switch embedding dimension from 768 (Ollama) to 1024 (Voyage voyage-4-large).
Existing embedding rows are cleared because dimensions are incompatible.

"""

from __future__ import annotations

from alembic import op

revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DELETE FROM transaction_embeddings")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat")
    op.execute(
        "ALTER TABLE transaction_embeddings "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING embedding::text::vector"
    )
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

    op.execute("DELETE FROM transaction_embeddings")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat")
    op.execute(
        "ALTER TABLE transaction_embeddings "
        "ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::text::vector"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tx_embeddings_hnsw "
        "ON transaction_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
