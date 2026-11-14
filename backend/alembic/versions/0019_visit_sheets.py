"""visit sheets

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visit_sheets",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("doctor", sa.String(120), nullable=True),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("family_notes", sa.String(2000), nullable=False, server_default=""),
        sa.Column("questions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("visit_sheets")
