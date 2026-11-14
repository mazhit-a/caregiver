"""scenario_answers

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("lesson_id", sa.String(64), nullable=False),
        sa.Column("screen_id", sa.String(64), nullable=False),
        sa.Column("answer_id", sa.String(64), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scenario_answers_session_id", "scenario_answers", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_scenario_answers_session_id", table_name="scenario_answers")
    op.drop_table("scenario_answers")
