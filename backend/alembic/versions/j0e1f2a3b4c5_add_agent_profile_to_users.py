"""Add agent_profile_json to users for persistent learned intelligence."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "j0e1f2a3b4c5"
down_revision = "i9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("agent_profile_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("users", "agent_profile_json")
