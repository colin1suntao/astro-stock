"""API routes for astro scoring + prediction."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas import AccuracyOut, AstroScoreOut, PredictionOut
from app.services import scoring

router = APIRouter(prefix="/api/stocks", tags=["scoring"])


def _validate_birth(birth: str | None) -> str | None:
    """Return birth unchanged if valid ISO datetime, else raise 422.

    P4-T5: explicit tzinfo fallback — naive datetimes treated as UTC by replacing
    tzinfo on the parsed datetime, so downstream consumers get a tz-aware ISO.
    """
    if birth is None:
        return birth
    try:
        dt = datetime.fromisoformat(birth)
    except ValueError:
        raise HTTPException(422, "birth must be an ISO 8601 datetime")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@router.get("/{ticker}/astro-score", response_model=AstroScoreOut)
async def astro_score(
    ticker: str,
    birth: str | None = Query(None, description="ISO 8601 birth datetime for personal fit"),
):
    return scoring.compute_score(ticker, birth_iso=_validate_birth(birth))


@router.get("/{ticker}/prediction", response_model=PredictionOut)
async def prediction(
    ticker: str,
    birth: str | None = Query(None, description="ISO 8601 birth datetime"),
):
    return scoring.predict_7day(ticker, birth_iso=_validate_birth(birth))


@router.get("/{ticker}/accuracy", response_model=AccuracyOut)
async def accuracy(ticker: str):
    return scoring.accuracy_for(ticker)
