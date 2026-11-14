"""saved_phrases

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_phrases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.String(300), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("lesson_id", sa.String(64), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saved_phrases_session_id", "saved_phrases", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_phrases_session_id", table_name="saved_phrases")
    op.drop_table("saved_phrases")
