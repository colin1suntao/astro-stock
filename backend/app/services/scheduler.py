"""Background scheduler — periodic transit scans for all users with birth charts.

APScheduler AsyncIOScheduler runs every 2h: walks users, calls transit_alert
scan_and_persist, logs new alerts. Lifecycle-managed by FastAPI lifespan
(start on startup, shutdown on stop).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services import transit_alert

log = logging.getLogger("scheduler")

_scheduler: AsyncIOScheduler | None = None
_SCAN_INTERVAL_MIN = 120  # 2h


async def _scan_all_users() -> None:
    """Walk every user with a birth chart, scan transits, persist new alerts."""
    db = SessionLocal()
    try:
        stmt = select(User).where(User.birth_iso != None)  # noqa: E711 — SQLAlchemy needs != None
        users = db.scalars(stmt).all()
        total_new = 0
        for u in users:
            try:
                new = transit_alert.scan_and_persist(u, db)
                total_new += len(new)
            except Exception as e:  # noqa — per-user resilience
                log.warning("scan user %s failed: %s", u.id, e)
        log.info("scan complete: %d users, %d new alerts (%s)",
                 len(users), total_new, datetime.now(timezone.utc).isoformat())
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    """Create + start the AsyncIO scheduler. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _scan_all_users,
        "interval",
        minutes=_SCAN_INTERVAL_MIN,
        id="transit_scan",
        next_run_time=datetime.now(timezone.utc),  # fire once on startup
        replace_existing=True,
    )
    _scheduler.start()
    log.info("scheduler started: transit scan every %d min", _SCAN_INTERVAL_MIN)
    return _scheduler


def stop_scheduler() -> None:
    """Shutdown scheduler on app stop. Idempotent."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    log.info("scheduler stopped")
