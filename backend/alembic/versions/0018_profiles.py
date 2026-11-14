"""profiles (non-medical page about the person being cared for)

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enjoys", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("calms", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("avoid", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("rhythm", sa.String(500), nullable=False, server_default=""),
        sa.Column("contacts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("caregiver_first_name", sa.String(40), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("profiles")
