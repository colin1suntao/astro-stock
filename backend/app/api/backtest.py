"""API routes for backtest."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import BacktestOut
from app.services import backtest

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/{ticker}", response_model=BacktestOut)
async def run(
    ticker: str,
    days: int = Query(60, ge=10, le=365),
    use_mock: bool = Query(True, description="false → real K-line (P2-2c)"),
):
    result = backtest.run_backtest(ticker, days=days, use_mock=use_mock)
    result["recommendations"] = backtest.recommend_weight_adjustments(result)
    return result
