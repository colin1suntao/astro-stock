"""Pydantic schemas for API I/O."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AspectType = Literal["conjunction", "opposition", "trine", "square", "sextile"]
Influence = Literal["positive", "neutral", "negative"]


class PlanetPosition(BaseModel):
    planet: str
    symbol: str
    sign: str
    sign_symbol: str
    degree: float = Field(..., description="Degree within sign, 0-30")
    degree_fmt: str
    longitude: float = Field(..., description="Ecliptic longitude 0-360")
    is_retrograde: bool = False
    house: int | None = None


class Aspect(BaseModel):
    planet1: str
    planet2: str
    type: AspectType
    orb: float
    influence: Influence


class MoonPhase(BaseModel):
    name: str
    illumination_pct: float
    phase_angle: float


class House(BaseModel):
    house: int
    sign: str
    cusp_deg: float


class BirthChart(BaseModel):
    birth_iso: str
    latitude: float
    longitude: float
    ascendant_deg: float
    ascendant_sign: tuple[str, str]
    houses: list[House]
    planets: list[PlanetPosition]
    aspects: list[Aspect]


class Transit(BaseModel):
    transiting_planet: str
    natal_planet: str
    type: AspectType
    orb: float


class HealthOut(BaseModel):
    status: str
    version: str


class StockQuote(BaseModel):
    ticker: str
    name: str
    price: float
    change_pct: float
    change: float
    prev_close: float
    open: float
    day_high: float
    high_52w: float = Field(..., alias="52w_high")
    low_52w: float = Field(..., alias="52w_low")
    volume: int
    market_cap: float
    pe: float
    prev_day_close: float
    fetched_at: str
    sector: str | None = None
    sector_label: str | None = None


class StockBar(BaseModel):
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: int


class StockHistory(BaseModel):
    ticker: str
    bars: list[StockBar]


class ScoreBreakdown(BaseModel):
    planetary: float
    aspect: float
    transit: float
    personal: float


class AstroScoreOut(BaseModel):
    ticker: str
    score: float
    direction: Literal["bull", "bear", "neutral"]
    direction_label: str
    direction_emoji: str
    breakdown: ScoreBreakdown
    computed_at: str


class PredictionBar(BaseModel):
    day_offset: int
    confidence: float


class PredictionOut(BaseModel):
    ticker: str
    base_score: float
    direction: Literal["bull", "bear", "neutral"]
    bars: list[PredictionBar]
    note: str


class AccuracyWindow(BaseModel):
    correct: int
    total: int
    pct: float


class AccuracyOut(BaseModel):
    ticker: str
    windows: dict[str, AccuracyWindow]
    note: str
