"""initial schema — users / holdings / predictions

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-17

Capture the tables that init_db() creates via Base.metadata.create_all.
Future schema changes get new revisions; this one seeds the baseline.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str | None, Sequence[str]] = None
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("pwd_hash", sa.String(255), nullable=False),
        sa.Column("birth_iso", sa.String(40), nullable=True),
        sa.Column("birth_lat", sa.Float, nullable=True),
        sa.Column("birth_lng", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("shares", sa.Integer, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_holdings_user"),
    )
    op.create_index("ix_holdings_user_id", "holdings", ["user_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("predicted_at", sa.DateTime, nullable=False),
        sa.Column("predicted_direction", sa.String(8), nullable=False),
        sa.Column("predicted_confidence", sa.Float, nullable=False),
        sa.Column("actual_result", sa.String(8), nullable=True),
        sa.Column("planetary_snapshot", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_predictions_user"),
    )
    op.create_index("ix_predictions_ticker", "predictions", ["ticker"])


def downgrade() -> None:
    op.drop_index("ix_predictions_ticker", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_holdings_user_id", table_name="holdings")
    op.drop_table("holdings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
