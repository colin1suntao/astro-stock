"""API routes for transit alerts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.services import transit_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: str
    triggered_at: str
    transiting_planet: str
    natal_planet: str
    aspect_type: str
    orb: float
    text: str
    read: bool


def _to_out(a) -> AlertOut:
    return AlertOut(
        id=a.id,
        triggered_at=a.triggered_at.isoformat() if hasattr(a.triggered_at, "isoformat") else str(a.triggered_at),
        transiting_planet=a.transiting_planet,
        natal_planet=a.natal_planet,
        aspect_type=a.aspect_type,
        orb=float(a.orb),
        text=a.text,
        read=bool(a.read),
    )


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    unread: bool = Query(False, description="true → 仅未读"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # opportunistic scan on each list call — persists new hits for today
    transit_alert.scan_and_persist(user, db)
    return [_to_out(a) for a in transit_alert.list_alerts(user, db, unread_only=unread)]


@router.post("/{alert_id}/read", response_model=AlertOut)
async def mark_read(
    alert_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not transit_alert.mark_read(alert_id, user, db):
        raise HTTPException(404, "alert not found")
    from sqlalchemy import select
    from app.models import Alert
    a = db.scalar(select(Alert).where(Alert.id == alert_id))
    return _to_out(a)


@router.post("/scan", response_model=list[AlertOut])
async def trigger_scan(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Force a transit scan — returns the new alerts created this call."""
    new = transit_alert.scan_and_persist(user, db)
    return [_to_out(a) for a in new]
