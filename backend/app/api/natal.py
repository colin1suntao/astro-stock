from fastapi import APIRouter, Query

from app.schemas import BirthChart, Transit
from app.services import ephem

router = APIRouter(tags=["natal"])


@router.get("/birth-chart", response_model=BirthChart)
async def birth_chart(
    birth: str = Query(..., description="ISO 8601 datetime of birth"),
    lat: float = Query(..., ge=-90, le=90, description="Birth latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Birth longitude"),
):
    return ephem.get_birth_chart(birth, lat, lon)


@router.get("/transits", response_model=list[Transit])
async def transits(
    birth: str = Query(..., description="ISO 8601 datetime of birth"),
    when: str | None = Query(None, description="ISO 8601; defaults to now"),
):
    return ephem.get_transits(birth, when)
