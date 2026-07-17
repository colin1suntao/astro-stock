"""Sector × planet heatmap — visualize which sectors arecurrently favored.

Each cell strength = sector weight × planet position quality
  friendly sign → 1.0, neutral → 0.5, detrimental → 0.0, retrograde ×0.6
Pluto rows aren't in ephem's 9 planets — cells strength=0.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services import ephem
from app.services.sector_map import SECTOR_PLANET_MAP
from app.services.scoring import SIGN_FRIENDLINESS

_PLANET_NAME = {
    "sun": "太阳", "moon": "月亮", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星",
    "uranus": "天王", "neptune": "海王",
}


def _strength(planet: str, sign: str | None, retro: bool) -> float:
    if not sign:
        return 0.0
    friendly, detrimental = SIGN_FRIENDLINESS.get(planet, ([], []))
    if sign in friendly:
        base = 1.0
    elif sign in detrimental:
        base = 0.0
    else:
        base = 0.5
    return round(base * (0.6 if retro else 1.0), 2)


def build_heatmap(when_iso: str | None = None) -> dict:
    positions = {p["planet"]: p for p in ephem.get_planet_positions(when_iso)}
    sectors = list(SECTOR_PLANET_MAP.keys())
    planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]

    cells: list[dict] = []
    for sk in sectors:
        sec = SECTOR_PLANET_MAP[sk]
        for pl in planets:
            pos = positions.get(pl)
            if pos:
                cells.append({
                    "sector": sk,
                    "sector_label": sec["label"],
                    "planet": pl,
                    "planet_name": _PLANET_NAME[pl],
                    "sign": pos["sign"],
                    "sign_symbol": pos["sign_symbol"],
                    "is_retrograde": bool(pos["is_retrograde"]),
                    "strength": _strength(pl, pos["sign"], bool(pos["is_retrograde"])) * sec["weight"],
                })
            else:
                cells.append({
                    "sector": sk, "sector_label": sec["label"],
                    "planet": pl, "planet_name": _PLANET_NAME[pl],
                    "sign": None, "sign_symbol": None, "is_retrograde": False,
                    "strength": 0.0,
                })
    # normalize strength to 0-1 (max possible = 1.0 × max weight = 1.4)
    max_s = max((c["strength"] for c in cells), default=1.0)
    for c in cells:
        c["strength"] = round(c["strength"] / max_s, 2)
    return {
        "sectors": sectors,
        "planets": planets,
        "cells": cells,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
