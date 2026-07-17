"""add alerts table — P2-3

Revision ID: 0002_alerts
Revises: 0001_initial
Create Date: 2026-07-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_alerts"
down_revision: Union[str | None, Sequence[str]] = "0001_initial"
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("triggered_at", sa.DateTime, nullable=False),
        sa.Column("transiting_planet", sa.String(16), nullable=False),
        sa.Column("natal_planet", sa.String(16), nullable=False),
        sa.Column("aspect_type", sa.String(16), nullable=False),
        sa.Column("orb", sa.Float, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("read", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_alerts_user"),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_user_read", "alerts", ["user_id", "read"])


def downgrade() -> None:
    op.drop_index("ix_alerts_user_read", table_name="alerts")
    op.drop_index("ix_alerts_user_id", table_name="alerts")
    op.drop_table("alerts")
