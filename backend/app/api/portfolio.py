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
