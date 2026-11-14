"""roleplay_runs (scores, goals, context, mode, timestamps; no text columns)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roleplay_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lesson_id", sa.String(64), nullable=False),
        sa.Column("context", sa.String(16), nullable=False),
        sa.Column("variant", sa.String(64), nullable=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("rounds_total", sa.Integer(), nullable=False),
        sa.Column(
            "turn_scores", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "goals_hit", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("context IN ('lesson', 'practice_round')", name="ck_roleplay_context"),
        sa.CheckConstraint("mode IN ('ai', 'fallback')", name="ck_roleplay_mode"),
    )
    op.create_index("ix_roleplay_runs_session_id", "roleplay_runs", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_roleplay_runs_session_id", table_name="roleplay_runs")
    op.drop_table("roleplay_runs")
