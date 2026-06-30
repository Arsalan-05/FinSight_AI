"""Bank connections (Plaid) and linked account fields."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "k1f2a3b4c5d6"
down_revision = "j0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="plaid"),
        sa.Column("item_id", sa.String(128), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("institution_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("institution_id", sa.String(64), nullable=True),
        sa.Column("transactions_cursor", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])

    op.add_column("accounts", sa.Column("plaid_account_id", sa.String(64), nullable=True))
    op.add_column("accounts", sa.Column("bank_connection_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_accounts_bank_connection",
        "accounts",
        "bank_connections",
        ["bank_connection_id"],
        ["id"],
    )
    op.create_index("ix_accounts_plaid_account_id", "accounts", ["plaid_account_id"])

    op.add_column("transactions", sa.Column("plaid_transaction_id", sa.String(64), nullable=True))
    op.create_index(
        "ix_transactions_plaid_transaction_id",
        "transactions",
        ["plaid_transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_plaid_transaction_id", "transactions")
    op.drop_column("transactions", "plaid_transaction_id")
    op.drop_constraint("fk_accounts_bank_connection", "accounts", type_="foreignkey")
    op.drop_index("ix_accounts_plaid_account_id", "accounts")
    op.drop_column("accounts", "bank_connection_id")
    op.drop_column("accounts", "plaid_account_id")
    op.drop_index("ix_bank_connections_user_id", "bank_connections")
    op.drop_table("bank_connections")
