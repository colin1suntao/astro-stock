"""SQLAlchemy declarative models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
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
