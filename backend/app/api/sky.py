"""Sky stream router — WebSocket (P5-1) supersedes SSE (P4-2).

GET /api/sky/stream  — legacy SSE (kept for backward compat)
WS  /ws/sky           — WebSocket: client sends subscribe {interval, planets}, server pushes snapshots

Snapshot payload same shape for both: {ts, positions[], aspects[], moon{}}.
For WS, optional `planets` whitelist filters positions to subscribed planets only.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

from app import schemas
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


def _filter_positions(snap: dict, planets: list[str] | None) -> dict:
    """Filter snapshot.positions to subscribed planets; None = all 9."""
    if not planets:
        return snap
    snap["positions"] = [p for p in snap["positions"] if p["planet"] in planets]
    return snap


@router.get("/stream")
async def stream(
    interval: int = Query(5, ge=1, le=60, description="seconds between pushes"),
):
    """SSE stream of sky snapshots (legacy P4-2). Closes when client disconnects."""
    async def gen():
        try:
            while True:
                snap = await _sky_snapshot()
                yield {"event": "sky", "data": json.dumps(snap, ensure_ascii=False)}
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return

    return EventSourceResponse(gen())


# P5-1: WebSocket endpoint — real bidirectional, client subscribes with {interval, planets}
# Mounted at app level as /ws/sky (see main.py include_router prefix)
@router.websocket("/ws")
async def sky_ws(ws: WebSocket):
    """WebSocket sky stream — client sends subscribe msg, server pushes snapshots.

    Client→Server messages:
      {"action":"subscribe","interval":10,"planets":["sun","moon"]}  — start/update
      {"action":"unsubscribe"}                                         — stop pushes
      {"action":"ping"}                                                — keepalive
    Server→Client messages:
      {"type":"snapshot","data":{ts,positions,aspects,moon}}
      {"type":"ack","action":"subscribe","interval":10,"planets":[...]}
      {"type":"error","message":"..."}
      {"type":"pong"}
    """
    await ws.accept()
    interval: int = 5
    planets: list[str] | None = None
    push_task: asyncio.Task | None = None

    async def push_loop():
        """Background loop: push filtered snapshot every `interval` seconds."""
        try:
            while True:
                snap = await _sky_snapshot()
                snap = _filter_positions(snap, planets)
                await ws.send_json({"type": "snapshot", "data": snap})
                await asyncio.sleep(interval)
        except (WebSocketDisconnect, asyncio.CancelledError):
            return
        except Exception as e:  # noqa — resilience, log to client
            try:
                await ws.send_json({"type": "error", "message": f"push failed: {type(e).__name__}"})
            except Exception:
                pass

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "invalid JSON"})
                continue
            action = msg.get("action")
            if action == "subscribe":
                interval = max(1, min(60, int(msg.get("interval", 5))))
                planets = msg.get("planets") or None
                # restart push loop with new params
                if push_task and not push_task.done():
                    push_task.cancel()
                push_task = asyncio.create_task(push_loop())
                await ws.send_json({"type": "ack", "action": "subscribe",
                                    "interval": interval, "planets": planets or "all"})
            elif action == "unsubscribe":
                if push_task and not push_task.done():
                    push_task.cancel()
                push_task = None
                await ws.send_json({"type": "ack", "action": "unsubscribe"})
            elif action == "ping":
                await ws.send_json({"type": "pong"})
            else:
                await ws.send_json({"type": "error", "message": f"unknown action: {action}"})
    except WebSocketDisconnect:
        if push_task and not push_task.done():
            push_task.cancel()


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


# P5-2a: AI 投资日历 — 全年重要相位日日历替当前相位聚合
_MOOD_MAP = {
    "trine": ("和谐助力，趋势顺向，可积极布局", "🌿"),
    "sextile": ("轻微助力，机会窗开，谨慎跟进", "🌱"),
    "conjunction": ("能量汇聚，方向不明，宜观望", "🔄"),
    "square": ("张力警示，趋势受阻，宜守不宜攻", "⚡"),
    "opposition": ("对冲拉锯，两面分化，严控风险", "⚔️"),
}


def _day_mood(snapped: list[dict]) -> tuple[str, str, float]:
    """From highlighted aspects (orb≤2°) derive one-sentence mood + emoji + 0-1 intensity.

    intensity = sum(1 - orb/2) across highlighted aspects, clipped to [0, 1].
    mood picks the aspect type with the highest aggregate intensity.
    """
    if not snapped:
        return "无精确相位，趋势平淡", "🌫️", 0.0
    by_type: dict[str, float] = {}
    by_type_count: dict[str, int] = {}
    intensity = 0.0
    for a in snapped:
        orb = float(a.get("orb", 2.0))
        w = max(0.0, 1.0 - orb / 2.0)
        intensity += w
        t = a["type"]
        by_type[t] = by_type.get(t, 0.0) + w
        by_type_count[t] = by_type_count.get(t, 0) + 1
    # dominant type by aggregate intensity
    dom = max(by_type.items(), key=lambda kv: kv[1])
    mood, emoji = _MOOD_MAP.get(dom[0], ("相位扰动，审时度势", "🌀"))
    return mood, emoji, min(1.0, intensity)


@router.get("/calendar", response_model=schemas.SkyCalendarOut)
async def calendar(
    year: int = Query(..., ge=1900, le=2100, description="year to scan"),
):
    """AI 投资日历 — 扫全年逐日抓 orb≤2° 精确相位日 + 投资 mood + intensity.

    替当前相位聚合：给前端一个日历视图，每日显重要相位 + 投资倾向 emoji。
    全年 365 日逐日跑 ephem.get_aspects（skyfield de421 真算），CPU 密集
    但单次约 1-3s，前端可缓存。
    """
    from datetime import date as _date, timedelta

    days: list[schemas.SkyCalendarDayOut] = []
    d = _date(year, 1, 1)
    end = _date(year + 1, 1, 1)
    while d < end:
        when_iso = f"{d.isoformat()}T12:00:00+00:00"  # noon UTC 稳定
        aspects = ephem.get_aspects(when_iso)
        snapped = [a for a in aspects if float(a.get("orb", 99)) <= 2.0]
        if snapped:  # 只录有精确相位的日（非 365 全录）
            mood, emoji, inten = _day_mood(snapped)
            days.append(schemas.SkyCalendarDayOut(
                date=d.isoformat(),
                aspects=snapped,
                mood=mood, mood_emoji=emoji, intensity=round(inten, 2),
            ))
        d += timedelta(days=1)

    return schemas.SkyCalendarOut(
        year=year,
        days=days,
        note=f"天象=skyfield de421.bsp 真算 · 全年逐日扫 orb≤2° 精确相位日 · {len(days)} 个相位日",
    )
