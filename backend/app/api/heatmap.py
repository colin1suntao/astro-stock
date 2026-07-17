"""API route for sector × planet heatmap."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import HeatmapOut
from app.services import heatmap

router = APIRouter(prefix="/api", tags=["heatmap"])


@router.get("/sector-heatmap", response_model=HeatmapOut)
async def sector_heatmap(
    when: str | None = Query(None, description="ISO datetime override"),
):
    return heatmap.build_heatmap(when_iso=when)
