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
