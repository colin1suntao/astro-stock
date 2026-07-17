"""Transit alert service — scan current transits vs user's natal chart.

For each transit hit with orb <= 2°, persist an Alert row with a short Chinese
description. Unread alerts surface on the Dashboard badge list.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, User
from app.services import ephem

_PLANET_CN = {
    "sun": "太阳", "moon": "月亮", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星",
    "uranus": "天王", "neptune": "海王",
}
_ASPECT_CN = {
    "conjunction": "合相", "opposition": "对冲", "trine": "三分",
    "square": "四分", "sextile": "六分",
}
_ASPECT_INFLUENCE = {
    "trine": "和谐助力", "sextile": "机缘助力",
    "square": "张力挑战", "opposition": "对峙压力",
    "conjunction": "能量共振",
}
_ORB_THRESHOLD = 2.0  # degrees — close hits only


def _describe(transiting: str, natal: str, aspect: str, orb: float) -> str:
    """Build a short Chinese description of one transit hit."""
    t_cn = _PLANET_CN.get(transiting, transiting)
    n_cn = _PLANET_CN.get(natal, natal)
    a_cn = _ASPECT_CN.get(aspect, aspect)
    infl = _ASPECT_INFLUENCE.get(aspect, "影响")
    return f"行运 {t_cn} 与本命 {n_cn} 形成 {a_cn}（容差 {orb}°），{infl}。"


def scan_and_persist(user: User, db: Session) -> list[Alert]:
    """Scan today's transits for `user`, persist new hits, return new Alerts.

    De-dups by (transiting, natal, aspect_type) within the same UTC day so repeated
    scans don't spam the table.
    """
    if not user.birth_iso:
        return []
    transits = ephem.get_transits(user.birth_iso)
    today = datetime.now(timezone.utc).date()

    # Fetch today's alerts for this user to de-dup
    existing = db.scalars(
        select(Alert).where(
            Alert.user_id == user.id,
            Alert.triggered_at >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
        )
    ).all()
    seen = {(a.transiting_planet, a.natal_planet, a.aspect_type) for a in existing}

    new_alerts: list[Alert] = []
    for t in transits:
        if t.get("orb", 99) > _ORB_THRESHOLD:
            continue
        key = (t["transiting_planet"], t["natal_planet"], t["type"])
        if key in seen:
            continue
        alert = Alert(
            user_id=user.id,
            transiting_planet=t["transiting_planet"],
            natal_planet=t["natal_planet"],
            aspect_type=t["type"],
            orb=float(t["orb"]),
            text=_describe(t["transiting_planet"], t["natal_planet"], t["type"], float(t["orb"])),
        )
        db.add(alert)
        new_alerts.append(alert)
    if new_alerts:
        db.commit()
        for a in new_alerts:
            db.refresh(a)
    return new_alerts


def list_alerts(user: User, db: Session, unread_only: bool = False) -> list[Alert]:
    """Return user's alerts, newest first."""
    stmt = select(Alert).where(Alert.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Alert.read == False)  # noqa: E712
    return list(db.scalars(stmt.order_by(Alert.triggered_at.desc())).all())


def mark_read(alert_id: str, user: User, db: Session) -> bool:
    """Mark one alert read. Returns True if found+updated, False if not owned."""
    a = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id))
    if not a:
        return False
    a.read = True
    db.commit()
    return True
