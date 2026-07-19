"""Sky stream router — Server-Sent Events for live sky updates (P4-2).

GET /api/sky/stream sends an event every `interval` seconds (default 5s):
  - positions: 9 planet ecliptic positions
  - aspects: current classical aspects
  - moon: phase + illumination
Client subscribes via EventSource in the frontend.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.services import ephem

router = APIRouter(prefix="/sky", tags=["sky"])


async def _sky_snapshot(when_iso: str | None = None) -> dict:
    """Build one sky snapshot dict."""
    positions = ephem.get_planet_positions(when_iso)
    aspects = ephem.get_aspects(when_iso)
    moon = ephem.get_moon_phase(when_iso)
    return {
        "ts": when_iso or datetime.now(timezone.utc).isoformat(),
        "positions": positions,
        "aspects": aspects,
        "moon": {"name": moon["name"], "illumination_pct": moon["illumination_pct"]},
    }


@router.get("/stream")
async def stream(
    interval: int = Query(5, ge=1, le=60, description="seconds between pushes"),
):
    """SSE stream of sky snapshots. Closes when client disconnects."""
    async def gen():
        try:
            while True:
                snap = await _sky_snapshot()
                yield {"event": "sky", "data": json.dumps(snap, ensure_ascii=False)}
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return

    return EventSourceResponse(gen())


@router.get("/history")
async def history(
    date: str = Query(..., description="ISO date or datetime, e.g. '1999-08-11' or '2026-07-19T12:00:00+08:00'"),
):
    """回看任意日天象 — 返回当时行星位置/相位/月相 + 重要相位日标星."""
    snap = await _sky_snapshot(date)
    # 标星：相位 orb≤2° 的视为「精确相位」标星
    snapped = [a for a in snap["aspects"] if a["orb"] <= 2.0]
    snap["highlighted_aspects"] = snapped
    snap["note"] = f"天象=skyfield de421.bsp 真算 · 时刻={date}"
    return snap
