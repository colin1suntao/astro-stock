"""API routes for stock market data."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import StockHistory, StockQuote
from app.services import market
from app.services.sector_map import sector_for, sector_label

router = APIRouter(prefix="/api/stocks", tags=["market"])


@router.get("/{ticker}", response_model=StockQuote)
async def quote(ticker: str):
    """Real-time quote for a US ticker via Sina."""
    q = market.get_quote(ticker)
    if not q:
        raise HTTPException(404, f"ticker {ticker} not found / source unavailable")
    q["sector"] = sector_for(ticker)
    q["sector_label"] = sector_label(q["sector"])
    return q


@router.get("/{ticker}/history", response_model=StockHistory)
async def history(
    ticker: str,
    count: int = Query(30, ge=1, le=365, description="number of daily bars"),
):
    bars = market.get_history(ticker, count=count)
    if not bars:
        raise HTTPException(404, f"no history for {ticker} / source unavailable")
    return StockHistory(ticker=ticker.upper(), bars=bars)
