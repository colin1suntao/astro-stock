"""add interpretations cache table — P3-2

Revision ID: 0003_interpretations
Revises: 0002_alerts
Create Date: 2026-07-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_interpretations"
down_revision: Union[str | None, Sequence[str]] = "0002_alerts"
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.create_table(
        "interpretations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("cache_key", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("tokens", sa.Integer, nullable=True),
        sa.Column("reasoning_tokens", sa.Integer, nullable=True),
        sa.Column("generated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_interpretations_cache_key", "interpretations",
                     ["cache_key"], unique=True)
    op.create_index("ix_interpretations_topic", "interpretations", ["topic"])
    op.create_index("ix_interpretations_ticker", "interpretations", ["ticker"])
    op.create_index("ix_interpretations_generated_at", "interpretations", ["generated_at"])
