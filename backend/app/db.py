"""Database session + table bootstrap."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite needs check_same_thread=False for FastAPI's thread pool
_connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}
engine = create_engine(settings.db_url, connect_args=_connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables (dev shortcut — use Alembic in prod)."""
    import os
    from app.models import Base  # noqa: avoid circular import at module load

    # SQLite path needs the directory to exist before first connection
    if settings.db_url.startswith("sqlite:///"):
        db_dir = settings.db_url.replace("sqlite:///", "").rsplit("/", 1)[0]
        os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a per-request Session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
