from datetime import datetime

from fastapi import APIRouter, Query

from app import __version__
from app.schemas import HealthOut
from app.services import ephem

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(status="ok", version=__version__)
