"""add user_id to chat_sessions for per-user chat scoping

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-29

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "user_id")
