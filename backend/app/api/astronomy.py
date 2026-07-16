from fastapi import APIRouter, Query

from app.schemas import Aspect, MoonPhase, PlanetPosition
from app.services import ephem

router = APIRouter(tags=["astronomy"])


@router.get("/planet-positions", response_model=list[PlanetPosition])
async def planet_positions(
    when: str | None = Query(None, description="ISO 8601 datetime; defaults to now"),
):
    return ephem.get_planet_positions(when)


@router.get("/aspects", response_model=list[Aspect])
async def aspects(
    when: str | None = Query(None, description="ISO 8601 datetime; defaults to now"),
):
    return ephem.get_aspects(when)


@router.get("/moon-phase", response_model=MoonPhase)
async def moon_phase(
    when: str | None = Query(None, description="ISO 8601 datetime; defaults to now"),
):
    return ephem.get_moon_phase(when)
