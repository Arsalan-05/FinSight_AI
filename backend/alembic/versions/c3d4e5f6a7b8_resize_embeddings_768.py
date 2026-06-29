"""resize_embeddings_768_for_ollama

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-29 14:00:00.000000

Switch default embedding dimension from 1024 (Voyage) to 768 (Ollama nomic-embed-text).
Existing embedding rows are cleared because dimensions are incompatible.

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM transaction_embeddings")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat")
    op.execute(
        "ALTER TABLE transaction_embeddings "
        "ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::text::vector"
    )
    op.execute(
        "CREATE INDEX idx_tx_embeddings_ivfflat "
        "ON transaction_embeddings "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM transaction_embeddings")
    op.execute("DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat")
    op.execute(
        "ALTER TABLE transaction_embeddings "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING embedding::text::vector"
    )
    op.execute(
        "CREATE INDEX idx_tx_embeddings_ivfflat "
        "ON transaction_embeddings "
        "USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
