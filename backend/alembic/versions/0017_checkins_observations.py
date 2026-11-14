"""checkins and observations

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checkins",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("lesson_id", sa.String(64), primary_key=True),
        sa.Column("came_up", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('helped', 'partly', 'didnt_help')",
            name="ck_checkins_outcome",
        ),
    )
    op.create_table(
        "observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lesson_id", sa.String(64), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("text", sa.String(300), nullable=False),
        sa.Column("add_to_visit_sheet", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('checkin_noted', 'doctor_note')", name="ck_observations_source"
        ),
    )
    op.create_index("ix_observations_session_id", "observations", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_observations_session_id", table_name="observations")
    op.drop_table("observations")
    op.drop_table("checkins")
