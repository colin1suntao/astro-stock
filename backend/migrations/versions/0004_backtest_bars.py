"""add backtest_bars table — P4-T3 per-bar persistence

Revision ID: 0004_backtest_bars
Revises: 0003_interpretations
Create Date: 2026-07-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_backtest_bars"
down_revision: Union[str | None, Sequence[str]] = "0003_interpretations"
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_bars",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("a_share_symbol", sa.String(16), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("predicted_direction", sa.String(16), nullable=False),
        sa.Column("actual_pct", sa.Float, nullable=False),
        sa.Column("correct", sa.Boolean, nullable=True),
        sa.Column("breakdown_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_bb_symbol", "backtest_bars", ["a_share_symbol"])
    op.create_index("ix_bb_date", "backtest_bars", ["date"])
    op.create_index("ix_bb_created", "backtest_bars", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_bb_created", table_name="backtest_bars")
    op.drop_index("ix_bb_date", table_name="backtest_bars")
    op.drop_index("ix_bb_symbol", table_name="backtest_bars")
    op.drop_table("backtest_bars")
