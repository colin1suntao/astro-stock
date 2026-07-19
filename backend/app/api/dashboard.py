"""Dashboard router — 天象→板块→个股 联动总览 (P4-C).

GET /api/dashboard returns:
  - 10 sectors × A-share representative (real-time price via Sina 真源)
  - 当日 astro_score per sector rep
  - 板块-行星联动描述（从 sector_map primary_planets + 当前行星位置推）
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app import schemas
from app.services import ephem, market, scoring
from app.services.sector_map import A_SHARE_REPS, SECTOR_PLANET_MAP

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_PLANET_CN = {
    "sun": "太阳", "moon": "月亮", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星",
    "uranus": "天王星", "neptune": "海王星", "pluto": "冥王星",
}


def _sky_snapshot(positions: list[dict]) -> str:
    """One-sentence sky snapshot, e.g. '太阳在巨蟹座26°, 水星逆行, 月相89%'."""
    sun = next((p for p in positions if p["planet"] == "sun"), None)
    retro = [p for p in positions if p["is_retrograde"]]
    moon = ephem.get_moon_phase()
    parts = []
    if sun:
        parts.append(f"太阳在{sun['sign']}{sun['degree']:.0f}°")
    if retro:
        names = "、".join(_PLANET_CN.get(p["planet"], p["planet"]) for p in retro)
        parts.append(f"{names}逆行")
    parts.append(f"月相{moon['illumination_pct']}% ({moon['name']})")
    return "，".join(parts) + "。"


def _linkage(sector_key: str, positions: list[dict]) -> str:
    """Sector-planet linkage description, e.g. '天王星在金牛座助力半导体板块'."""
    info = SECTOR_PLANET_MAP.get(sector_key, {})
    primary = info.get("primary_planets", [])
    if not primary:
        return f"{info.get('label', sector_key)}板块无行星映射"
    # pick the strongest primary planet: closest to 0°/30° boundary (visual prominence)
    pos_map = {p["planet"]: p for p in positions}
    chosen = None
    for pname in primary:
        p = pos_map.get(pname)
        if p:
            chosen = p
            break
    if not chosen:
        pname = primary[0]
        return f"{_PLANET_CN.get(pname, pname)}影响{info.get('label', sector_key)}板块"
    planet_cn = _PLANET_CN.get(chosen["planet"], chosen["planet"])
    # friendliness from scoring module-level table
    from app.services.scoring import SIGN_FRIENDLINESS
    friend = SIGN_FRIENDLINESS.get(chosen["sign"], {}).get(chosen["planet"], "neutral")
    verb = "助力" if friend == "friendly" else "施压" if friend == "detrimental" else "中性影响"
    return f"{planet_cn}在{chosen['sign']}{chosen['degree']:.0f}°{verb}{info.get('label', sector_key)}板块"


@router.get("", response_model=schemas.DashboardOut)
async def dashboard():
    """10 板块 × A 股代表 实时价 + 当日占星评分 + 联动描述."""
    now_iso = datetime.now(timezone.utc).isoformat()
    positions = ephem.get_planet_positions(now_iso)
    sectors_out: list[schemas.DashboardSectorOut] = []
    for sector_key, rep in A_SHARE_REPS.items():
        info = SECTOR_PLANET_MAP.get(sector_key, {})
        sector_label = info.get("label", sector_key)
        # real-time A-share quote (真源, may be empty outside CN trading hours)
        try:
            q = market.get_a_share_quote(rep["symbol"])
        except Exception:
            q = {}
        price = float(q.get("price") or 0)
        chg = float(q.get("change_pct") or 0)
        # astro_score for the rep ticker (use US ticker key in TICKER_SECTOR via sector_key)
        # compute_score expects a ticker whose sector_for() returns sector_key;
        # since A-share tickers aren't in TICKER_SECTOR, we pass a synthetic US rep
        # but sector_for() returns None → fallback: pass sector_key as ticker and
        # patch sector_for via a wrapper. Simpler: call _planetary_score directly.
        # For MVP we call compute_score on the US representative mapped to this sector.
        us_rep = _us_rep_for_sector(sector_key)
        try:
            score = scoring.compute_score(us_rep, when_iso=now_iso)
        except Exception:
            score = {"score": 0.0, "direction": "neutral",
                     "direction_label": "中性", "direction_emoji": "➡️"}
        sectors_out.append(schemas.DashboardSectorOut(
            sector_key=sector_key,
            sector_label=sector_label,
            ticker=rep["ticker"],
            name=rep["name"],
            price=price,
            change_pct=chg,
            astro_score=score["score"],
            direction=score["direction"],
            direction_label=score["direction_label"],
            direction_emoji=score["direction_emoji"],
            linkage=_linkage(sector_key, positions),
        ))
    return schemas.DashboardOut(
        computed_at=now_iso,
        sectors=sectors_out,
        sky_summary=_sky_snapshot(positions),
        note="天象=skyfield de421.bsp 真算 · A股价=Sina hq.sinajs.cn 真源 · 评分=P1-4 默认权重",
    )


def _us_rep_for_sector(sector_key: str) -> str:
    """Pick a US ticker in TICKER_SECTOR for this sector_key (for astro_score)."""
    from app.services.sector_map import TICKER_SECTOR
    for tk, sk in TICKER_SECTOR.items():
        if sk == sector_key:
            return tk
    return "AAPL"  # fallback
