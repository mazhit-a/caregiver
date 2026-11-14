"""stripe test clock id and billing sync on subscriptions

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("stripe_test_clock_id", sa.String(64), nullable=True))
    op.add_column(
        "subscriptions", sa.Column("stripe_clock_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "subscriptions",
        sa.Column("billing_sync", sa.String(8), nullable=False, server_default="none"),
    )
    op.create_index(
        "ix_subscriptions_stripe_test_clock_id", "subscriptions", ["stripe_test_clock_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_stripe_test_clock_id", table_name="subscriptions")
    op.drop_column("subscriptions", "billing_sync")
    op.drop_column("subscriptions", "stripe_clock_at")
    op.drop_column("subscriptions", "stripe_test_clock_id")
