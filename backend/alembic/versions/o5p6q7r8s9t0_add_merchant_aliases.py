"""Add merchant_aliases table (v2.0 ingest depth).

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-09-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "o5p6q7r8s9t0"
down_revision = "n4o5p6q7r8s9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_aliases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("raw_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="normalize"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_merchant_aliases_user_id", "merchant_aliases", ["user_id"])
    op.create_index("ix_merchant_aliases_raw_name", "merchant_aliases", ["raw_name"])


def downgrade() -> None:
    op.drop_index("ix_merchant_aliases_raw_name", table_name="merchant_aliases")
    op.drop_index("ix_merchant_aliases_user_id", table_name="merchant_aliases")
    op.drop_table("merchant_aliases")
