"""plans and confidence

Revision ID: 0007
Revises: 0010
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rules_version", sa.Integer(), nullable=False),
        sa.Column("content_version", sa.String(64), nullable=False),
        sa.Column("lessons_per_week", sa.Integer(), nullable=False),
        sa.Column("gift_phrase_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "confidence",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("day0", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("confidence")
    op.drop_table("plans")
