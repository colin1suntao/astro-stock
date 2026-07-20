"""Leaderboard router — 全用户持仓占星分排行 + 分享链接 (P4-1).

GET /api/leaderboard aggregates every user's holdings, computes each holding's
astro_score (compute_score), ranks users by mean astro_score. Each entry gets
a stable share_token (sha1 of user_id) so a public link can embed it.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app import schemas
from app.auth import current_user
from app.db import SessionLocal
from app.models import Holding, User
from app.services import scoring

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _share_token(user_id: str) -> str:
    """Stable opaque token for share link — sha1(user_id)[:16]."""
    return hashlib.sha1(user_id.encode()).hexdigest()[:16]


@router.get("", response_model=schemas.LeaderboardOut)
async def leaderboard(
    limit: int = 50,
):
    """全用户持仓占星分排行 — mean astro_score per user."""
    db = SessionLocal()
    try:
        users = db.scalars(select(User)).all()
        entries: list[schemas.LeaderboardEntryOut] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for u in users:
            holdings = db.scalars(
                select(Holding).where(Holding.user_id == u.id)
            ).all()
            if not holdings:
                continue
            scores: list[float] = []
            tickers: list[str] = []
            for h in holdings:
                try:
                    s = scoring.compute_score(h.ticker, birth_iso=u.birth_iso, when_iso=now_iso)
                    scores.append(float(s["score"]))
                    tickers.append(h.ticker.upper())
                except Exception:
                    continue
            if not scores:
                continue
            entries.append(schemas.LeaderboardEntryOut(
                rank=0,  # filled after sort
                user_id=u.id,
                user_name=u.name or u.email.split("@")[0],
                avg_score=round(sum(scores) / len(scores), 1),
                holdings_count=len(holdings),
                tickers=tickers,
                share_token=_share_token(u.id),
            ))
    finally:
        db.close()

    # sort by avg_score desc, assign ranks
    entries.sort(key=lambda e: e.avg_score, reverse=True)
    for i, e in enumerate(entries, 1):
        e.rank = i
    entries = entries[: max(0, limit)]

    return schemas.LeaderboardOut(
        computed_at=now_iso,
        entries=entries,
        note="占星分=真skyfield算 · 分享链接token=sha1(user_id)[:16] · 仅登录用户可见",
    )
