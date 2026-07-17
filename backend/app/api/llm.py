"""API route for LLM interpretation."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import InterpretOut
from app.services import llm

router = APIRouter(prefix="/api/interpret", tags=["llm"])


@router.get("", response_model=InterpretOut)
async def interpret(
    topic: str = Query(..., description="解读话题，如「当前天象对半导体板块的影响」"),
    ticker: str | None = Query(None, description="关联个股，可选"),
    birth: str | None = Query(None, description="ISO 8601 birth datetime for personal fit"),
):
    return llm.interpret(topic, ticker=ticker, birth_iso=birth)
