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


class BacktestBar(BaseModel):
    date: str
    score: float
    predicted_direction: Literal["bull", "bear", "neutral"]
    actual_pct: float
    correct: bool | None


class DirectionStat(BaseModel):
    total: int
    correct: int
    accuracy: float


class WeightRec(BaseModel):
    issue: str
    fix: str


class BacktestOut(BaseModel):
    ticker: str
    days: int
    data_source: str
    overall_accuracy: float
    scored_count: int
    neutral_count: int
    by_direction: dict[str, DirectionStat]
    sample_bars: list[BacktestBar]
    recommendations: list[WeightRec]


class HeatmapCell(BaseModel):
    sector: str
    sector_label: str
    planet: str
    planet_name: str
    sign: str | None
    sign_symbol: str | None
    is_retrograde: bool
    strength: float  # 0-1 normalized influence intensity


class HeatmapOut(BaseModel):
    sectors: list[str]  # row keys in order
    planets: list[str]  # col keys in order
    cells: list[HeatmapCell]
    computed_at: str


class InterpretOut(BaseModel):
    text: str
    model: str
    tokens: int | None = None
    reasoning_tokens: int | None = None
    topic: str
    ticker: str | None = None
    generated_at: str
    cached: bool = False


class DashboardSectorOut(BaseModel):
    sector_key: str
    sector_label: str
    ticker: str           # human ticker (e.g. 'MOUTAI')
    name: str             # CN display name (e.g. '贵州茅台')
    price: float
    change_pct: float
    astro_score: float
    direction: Literal["bull", "bear", "neutral"]
    direction_label: str
    direction_emoji: str
    linkage: str          # e.g. '天王星在金牛座助力科技板块'


class DashboardOut(BaseModel):
    computed_at: str
    sectors: list[DashboardSectorOut]
    sky_summary: str      # 1-sentence current sky snapshot
    note: str             # data source attribution


class SkyCalendarDayOut(BaseModel):
    date: str                  # YYYY-MM-DD
    aspects: list[Aspect]       # highlighted aspects orb≤2°
    mood: str                  # one-sentence investor mood from aspects
    mood_emoji: str
    intensity: float           # 0-1 normalized aspect intensity for the day


class SkyCalendarOut(BaseModel):
    year: int
    days: list[SkyCalendarDayOut]
    note: str


class LeaderboardEntryOut(BaseModel):
    rank: int
    user_id: str
    user_name: str
    avg_score: float          # mean astro_score across holdings
    holdings_count: int
    tickers: list[str]
    share_token: str          # opaque token for public share link


class LeaderboardOut(BaseModel):
    computed_at: str
    entries: list[LeaderboardEntryOut]
    note: str


class HoldingAttributionOut(BaseModel):
    ticker: str
    shares: int
    entry_price: float
    current_price: float       # A-share realtime (0 if source unavailable)
    pnl: float                 # unrealized P&L in CNY
    pnl_pct: float             # unrealized P&L %
    astro_score: float
    direction: Literal["bull", "bear", "neutral"]
    direction_label: str
    direction_emoji: str
    breakdown: dict            # per-component contribution to score
    planetary_linkage: str     # human-readable planetary attribution


class PortfolioAttributionOut(BaseModel):
    computed_at: str
    user_name: str
    holdings: list[HoldingAttributionOut]
    total_pnl: float
    # 风险敞口按行星分布：sum astro_score weighted by pnl across holdings per primary planet
    planet_exposure: dict[str, float]
    note: str
