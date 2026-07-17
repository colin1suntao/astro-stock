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
    use_mock: bool = Query(True, description="false → real K-line"),
    a_share: str | None = Query(None, description="A-share symbol for real data, e.g. sh600519"),
):
    result = backtest.run_backtest(
        ticker, days=days, use_mock=use_mock, a_share_symbol=a_share,
    )
    result["recommendations"] = backtest.recommend_weight_adjustments(result)
    return result


@router.post("/tune", response_model=dict)
async def tune(
    tickers: list[str] = Query(..., description="scoring keys to backtest"),
    a_shares: list[str] = Query(..., description="matching A-share symbols"),
    days: int = Query(60, ge=10, le=365),
):
    """Run backtest on each ticker×a_share, then scipy.optimize weights."""
    results = []
    for tk, a_sh in zip(tickers, a_shares):
        r = backtest.run_backtest(tk, days=days, use_mock=False, a_share_symbol=a_sh)
        r["recommendations"] = backtest.recommend_weight_adjustments(r)
        results.append(r)
    return backtest.tune_weights(results)
