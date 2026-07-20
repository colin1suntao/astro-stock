"""SQLAlchemy declarative models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    pwd_hash: Mapped[str] = mapped_column(String(255))
    # Astro identity (nullable until set)
    birth_iso: Mapped[str | None] = mapped_column(String(40), nullable=True)
    birth_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    holdings: Mapped[list["Holding"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Holding(Base):
    """One portfolio row: ticker + shares + entry price."""
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(16))
    shares: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="holdings")


class Alert(Base):
    """Transit-triggered alert for a user."""
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    transiting_planet: Mapped[str] = mapped_column(String(16))
    natal_planet: Mapped[str] = mapped_column(String(16))
    aspect_type: Mapped[str] = mapped_column(String(16))
    orb: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(back_populates="alerts")


class Interpretation(Base):
    """LLM interpretation cache — keyed by (topic, ticker, YYYY-MM-DD)."""
    __tablename__ = "interpretations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(60))
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class BacktestBar(Base):
    """Per-bar backtest snapshot — persisted for analytics/regression (P4-T3)."""
    __tablename__ = "backtest_bars"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    a_share_symbol: Mapped[str] = mapped_column(String(16), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)          # YYYY-MM-DD
    score: Mapped[float] = mapped_column(Float)
    predicted_direction: Mapped[str] = mapped_column(String(16))
    actual_pct: Mapped[float] = mapped_column(Float)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # per-component contributions (JSON-serializable breakdown dict)
    breakdown_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )


class PredictionRecord(Base):
    """Historical prediction for accuracy tracking (P2 populates)."""
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    predicted_direction: Mapped[str] = mapped_column(String(8))
    predicted_confidence: Mapped[float] = mapped_column(Float)
    actual_result: Mapped[str | None] = mapped_column(String(8), nullable=True)  # correct|incorrect|partial
    planetary_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob


class SkyCalendarCache(Base):
    """P5-3: 投资日历缓存 — keyed by year, JSON blob + TTL 30 天。

    全年逐日跑 ephem.get_aspects 耗时 ~5s，缓存后同 year 请求 <50ms。
    """
    __tablename__ = "sky_calendar_cache"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    year: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text)          # SkyCalendarOut dict JSON
    phase_days: Mapped[int] = mapped_column(Integer)         # len(days) for quick sanity
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # TTL 30 天后过期
