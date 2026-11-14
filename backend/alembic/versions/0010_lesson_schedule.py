"""lesson_schedule

Revision ID: 0010
Revises: 0002
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_schedule",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("lesson_id", sa.String(64), primary_key=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("unlock_on", sa.Date(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lesson_schedule")
