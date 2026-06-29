"""add title to chat_sessions for history sidebar

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-06-29

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "h8c9d0e1f2a3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "title")
