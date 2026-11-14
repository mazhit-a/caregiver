"""events

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("props", JSONB(), nullable=False, server_default="{}"),
        sa.Column("app_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_session_id", "events", ["session_id"])
    op.create_index("ix_events_name", "events", ["name"])


def downgrade() -> None:
    op.drop_index("ix_events_name", table_name="events")
    op.drop_index("ix_events_session_id", table_name="events")
    op.drop_table("events")
