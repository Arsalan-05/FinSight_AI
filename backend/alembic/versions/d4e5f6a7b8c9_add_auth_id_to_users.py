"""add auth_id to users for Supabase linking

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-29

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_id", sa.String(length=36), nullable=True))
    op.create_index("ix_users_auth_id", "users", ["auth_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_auth_id", table_name="users")
    op.drop_column("users", "auth_id")
