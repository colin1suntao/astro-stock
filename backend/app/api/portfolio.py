"""Portfolio CRUD — current user's holdings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import Holding, User

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class HoldingIn(BaseModel):
    ticker: str
    shares: int
    entry_price: float
    note: str | None = None


class HoldingOut(BaseModel):
    id: str
    ticker: str
    shares: int
    entry_price: float
    note: str | None


@router.get("", response_model=list[HoldingOut])
async def list_holdings(user: User = Depends(current_user)):
    return [
        HoldingOut(id=h.id, ticker=h.ticker, shares=h.shares,
                   entry_price=h.entry_price, note=h.note)
        for h in user.holdings
    ]


@router.post("", response_model=HoldingOut, status_code=201)
async def add_holding(
    body: HoldingIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    h = Holding(user_id=user.id, ticker=body.ticker.upper(),
                shares=body.shares, entry_price=body.entry_price, note=body.note)
    db.add(h); db.commit(); db.refresh(h)
    return HoldingOut(id=h.id, ticker=h.ticker, shares=h.shares,
                      entry_price=h.entry_price, note=h.note)


@router.delete("/{holding_id}", status_code=204)
async def delete_holding(
    holding_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    h = db.scalar(select(Holding).where(Holding.id == holding_id, Holding.user_id == user.id))
    if not h:
        raise HTTPException(404, "holding not found")
    db.delete(h); db.commit()


# P4-6a: 持仓盈亏占星归因 — 真实时 A 股价 + 占星归因
from datetime import datetime, timezone
from app import schemas
from app.services import ephem, market, scoring
from app.services.sector_map import A_SHARE_REPS, SECTOR_PLANET_MAP, TICKER_SECTOR

_PLANET_CN = {
    "sun": "太阳", "moon": "月亮", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星",
    "uranus": "天王星", "neptune": "海王星", "pluto": "冥王星",
}


def _a_share_for_ticker(ticker: str) -> str | None:
    """Pick an A-share Sina symbol for a US ticker via its sector."""
    sec = TICKER_SECTOR.get(ticker.upper())
    if not sec or sec not in A_SHARE_REPS:
        return None
    return A_SHARE_REPS[sec]["symbol"]


def _planetary_linkage(ticker: str, positions: list[dict]) -> str:
    """Human-readable planetary attribution for a holding's sector."""
    sec = TICKER_SECTOR.get(ticker.upper())
    if not sec:
        return "未知板块"
    info = SECTOR_PLANET_MAP.get(sec, {})
    primaries = info.get("primary_planets", [])
    pos_map = {p["planet"]: p for p in positions}
    chosen = None
    for pname in primaries:
        p = pos_map.get(pname)
        if p:
            chosen = p
            break
    if not chosen:
        return f"{info.get('label', sec)}板块受 {_PLANET_CN.get(primaries[0], primaries[0]) if primaries else '未知'} 影响"
    planet_cn = _PLANET_CN.get(chosen["planet"], chosen["planet"])
    friend = scoring.SIGN_FRIENDLINESS.get(chosen["planet"], ([], []))
    if chosen["sign"] in friend[0]:
        verb = "助力"
    elif chosen["sign"] in friend[1]:
        verb = "施压"
    else:
        verb = "中性影响"
    return f"{planet_cn}在{chosen['sign']}{chosen['degree']:.0f}°{verb}{info.get('label', sec)}板块"


@router.get("/attribution", response_model=schemas.PortfolioAttributionOut)
async def attribution(user: User = Depends(current_user)):
    """每持仓真实时盈亏 + 占星归因 + 风险敞口按行星分布."""
    now_iso = datetime.now(timezone.utc).isoformat()
    positions = ephem.get_planet_positions(now_iso)
    holdings_out: list[schemas.HoldingAttributionOut] = []
    total_pnl = 0.0
    planet_exposure: dict[str, float] = {}

    for h in user.holdings:
        # realtime A-share price via Sina (真源, fallback 0 if unreachable)
        a_sym = _a_share_for_ticker(h.ticker)
        cur_price = 0.0
        if a_sym:
            try:
                q = market.get_a_share_quote(a_sym)
                cur_price = float(q.get("price") or 0)
            except Exception:
                cur_price = 0.0
        pnl = round((cur_price - h.entry_price) * h.shares, 2) if cur_price else 0.0
        pnl_pct = round((cur_price - h.entry_price) / h.entry_price * 100, 2) if cur_price and h.entry_price else 0.0
        total_pnl += pnl

        # astro_score + breakdown
        try:
            s = scoring.compute_score(h.ticker, birth_iso=user.birth_iso, when_iso=now_iso)
            score = float(s["score"])
            direction = s["direction"]
            d_label = s["direction_label"]
            d_emoji = s["direction_emoji"]
            breakdown = s.get("breakdown", {})
        except Exception:
            score, direction, d_label, d_emoji, breakdown = 0.0, "neutral", "中性", "➡️", {}

        linkage = _planetary_linkage(h.ticker, positions)
        # risk exposure: weight score by |pnl| to the sector's primary planets
        sec = TICKER_SECTOR.get(h.ticker.upper())
        if sec:
            for pname in SECTOR_PLANET_MAP.get(sec, {}).get("primary_planets", []):
                # exposure = score × |pnl|; spread across primary planets
                planet_exposure[pname] = planet_exposure.get(pname, 0.0) + score * abs(pnl)

        holdings_out.append(schemas.HoldingAttributionOut(
            ticker=h.ticker.upper(), shares=h.shares, entry_price=h.entry_price,
            current_price=cur_price, pnl=pnl, pnl_pct=pnl_pct,
            astro_score=score, direction=direction, direction_label=d_label,
            direction_emoji=d_emoji, breakdown=breakdown, planetary_linkage=linkage,
        ))

    return schemas.PortfolioAttributionOut(
        computed_at=now_iso,
        user_name=user.name or user.email.split("@")[0],
        holdings=holdings_out,
        total_pnl=round(total_pnl, 2),
        planet_exposure={k: round(v, 2) for k, v in planet_exposure.items()},
        note="盈亏=A股真源Sina · 占星归因=真skyfield算 · 风险敞口=Σ(score×|pnl|) per primary planet",
    )
