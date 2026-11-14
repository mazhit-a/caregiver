"""if_then_plans, tasks, confidence first/latest

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("confidence", sa.Column("first", postgresql.JSONB(), nullable=True))
    op.add_column("confidence", sa.Column("latest", postgresql.JSONB(), nullable=True))
    # A row can now exist before the quiz stored Q11 (ratings saved on their own).
    op.alter_column("confidence", "day0", existing_type=sa.Integer(), nullable=True)
    op.create_table(
        "if_then_plans",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("lesson_id", sa.String(64), primary_key=True),
        sa.Column("cue", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("reset", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "tasks",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("lesson_id", sa.String(64), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reminder_downloaded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("if_then_plans")
    op.execute("DELETE FROM confidence WHERE day0 IS NULL")
    op.alter_column("confidence", "day0", existing_type=sa.Integer(), nullable=False)
    op.drop_column("confidence", "latest")
    op.drop_column("confidence", "first")
