"""Sky stream router — WebSocket (P5-1) supersedes SSE (P4-2).

GET /api/sky/stream  — legacy SSE (kept for backward compat)
WS  /ws/sky           — WebSocket: client sends subscribe {interval, planets}, server pushes snapshots

Snapshot payload same shape for both: {ts, positions[], aspects[], moon{}}.
For WS, optional `planets` whitelist filters positions to subscribed planets only.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta
from functools import lru_cache

from fastapi import APIRouter, Query, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app import schemas
from app.db import SessionLocal
from app.models import SkyCalendarCache
from app.services import ephem

router = APIRouter(prefix="/sky", tags=["sky"])

# P5-3a: 缓存层常量
_CAL_TTL_DAYS = 30          # 缓存有效期 30 天（年过完即稳，TTL 防星历表微调或 ephem 升级后陈旧）
_CAL_LRU_MAX = 8            # 进程内 LRU 最多缓存 8 个年（近 10 年用），超则淘汰最旧


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


# P5-3a: 进程内 LRU 一层 — 避免热年每请求查 SQLite（~50ms 盘存）
# typed as dict[int, dict] — 快照直返，跳过 JSON 反序列
@lru_cache(maxsize=_CAL_LRU_MAX)
def _calendar_inmem(year: int) -> dict | None:
    """Return SkyCalendarOut dict if cached & fresh in SQLite, else None."""
    db = SessionLocal()
    try:
        row = db.scalar(select(SkyCalendarCache).where(SkyCalendarCache.year == year))
        if not row:
            return None
        if datetime.now(timezone.utc) > row.expires_at.replace(tzinfo=timezone.utc):
            return None  # expired → 让 calendar 真算并刷新
        return json.loads(row.payload_json)
    finally:
        db.close()


def _calendar_persist(year: int, payload: dict, phase_days: int) -> None:
    """Upsert calendar into SQLite + warm in-mem LRU."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=_CAL_TTL_DAYS)
    db = SessionLocal()
    try:
        row = db.scalar(select(SkyCalendarCache).where(SkyCalendarCache.year == year))
        if row:
            row.payload_json = json.dumps(payload, ensure_ascii=False)
            row.phase_days = phase_days
            row.created_at = now
            row.expires_at = expires
        else:
            db.add(SkyCalendarCache(
                year=year, payload_json=json.dumps(payload, ensure_ascii=False),
                phase_days=phase_days, created_at=now, expires_at=expires,
            ))
        db.commit()
    finally:
        db.close()
    _calendar_inmem.cache_clear()  # 下一请求重读，避免 stale


async def _calendar_compute(year: int) -> dict:
    """真算全年 — 耗时 ~5s，只在缓存 miss 时跑."""
    from datetime import date as _date

    days: list[dict] = []
    d = _date(year, 1, 1)
    end = _date(year + 1, 1, 1)
    while d < end:
        when_iso = f"{d.isoformat()}T12:00:00+00:00"  # noon UTC 稳定
        aspects = ephem.get_aspects(when_iso)
        snapped = [a for a in aspects if float(a.get("orb", 99)) <= 2.0]
        if snapped:  # 只录有精确相位的日（非 365 全录）
            mood, emoji, inten = _day_mood(snapped)
            days.append({
                "date": d.isoformat(),
                "aspects": snapped,
                "mood": mood, "mood_emoji": emoji, "intensity": round(inten, 2),
            })
        d += timedelta(days=1)
    return {
        "year": year,
        "days": days,
        "note": f"天象=skyfield de421.bsp 真算 · 全年逐日扫 orb≤2° 精确相位日 · {len(days)} 个相位日",
    }


# P5-3b: HTTP 响应头 — 浏览器/CDN 层缓存对梡
_CAL_CC = f"public, max-age={_CAL_TTL_DAYS * 86400}"  # 30 天 immutable（year 内容稳定）
import hashlib as _hashlib


def _calendar_etag(payload: dict) -> str:
    """Stable Etag from payload hash — client If-None-Match 命中则 304."""
    h = _hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return f'"sky-cal-{h[:16]}"'


@router.get("/calendar", response_model=schemas.SkyCalendarOut)
async def calendar(
    year: int = Query(..., ge=1900, le=2100, description="year to scan"),
    req: Request = None,
    res: Response = None,
):
    """AI 投资日历 — 全年重要相位日 + 投资倾向（P5-2）+ SQLite 缓存层（P5-3a）+ HTTP 响应头（P5-3b）.

    缓存三层：进程内 LRU → SQLite 持久（TTL 30 天）→ miss 时真算 ~5s 填入。
    HTTP 头：Cache-Control public max-age=30d + ETag → 浏览器 If-None-Match 命中返 304。
    """
    # LRU 一层
    cached = _calendar_inmem(year)
    payload = cached if cached is not None else None
    if payload is None:
        # SQLite 二层（_calendar_inmem 已查 SQLite，miss 时返 None → 真算）
        payload = await _calendar_compute(year)
        _calendar_persist(year, payload, len(payload["days"]))
    # P5-3b: 注响应头 + If-None-Match 命中返 304（跳 body）
    etag = _calendar_etag(payload)
    res.headers["Cache-Control"] = _CAL_CC
    res.headers["ETag"] = etag
    res.headers["Vary"] = "Accept-Encoding"
    inm = req.headers.get("if-none-match")
    if inm and inm == etag:
        res.status_code = 304
        res.body = b""  # 304 不含 body，显式置空避 response_model 序列化 None 报错
        return res  # 返 Response 跳过 response_model 序列化
    return payload
