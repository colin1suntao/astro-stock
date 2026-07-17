"""AstroScore engine — combines ephem + market + sector_map into a 0-100 score.

Algorithm (from docs/design-doc.md §8.1):
    Score = PlanetaryWeight × 40 + AspectScore × 30 + TransitMatch × 20 + PersonalFit × 10

Each component is scored 0..1 then multiplied by its weight; the final 0..100
score maps to a prediction direction via §8.2 bands.

This is the MVP heuristic — weights and curves are hand-tuned and will be
regression-tested in P2 against historical data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services import ephem, market
from app.services.sector_map import SECTOR_PLANET_MAP, sector_for


# --- prediction bands (§8.2) -----------------------------------------------

def direction_of(score: float) -> dict:
    """Map 0-100 score → direction band dict {direction, label, emoji, color}."""
    if score >= 75:
        return {"direction": "bull", "label": "强烈看涨", "emoji": "🚀", "color": "success"}
    if score >= 60:
        return {"direction": "bull", "label": "温和看涨", "emoji": "📈", "color": "success"}
    if score >= 40:
        return {"direction": "neutral", "label": "中性观望", "emoji": "⚖️", "color": "warning"}
    if score >= 25:
        return {"direction": "bear", "label": "温和看跌", "emoji": "📉", "color": "warning"}
    return {"direction": "bear", "label": "强烈看跌", "emoji": "🔻", "color": "danger"}


# --- component scorers (each returns 0..1 + breakdown detail) --------------

def _planetary_score(ticker: str, positions: list[dict]) -> tuple[float, list[dict]]:
    """Score how well current planets match the ticker's sector.

    For each planet in the sector's primary_planets, give points if the planet
    is in a "friendly" zodiac sign (fire/air signs boost tech, earth/water
    boost finance, etc.). MVP simplification: boost if planet is NOT in
    detrimental sign; more nuance deferred to P2.
    """
    sector_key = sector_for(ticker)
    if not sector_key:
        return 0.5, [{"note": "unknown sector", "pts": 0.5}]
    sector = SECTOR_PLANET_MAP[sector_key]
    primaries = sector["primary_planets"]
    weight = sector["weight"]

    # Friendly/detrimental signs per planet (MVP). Triple-valued so each planet
    # has both friendly (+1.0) and detrimental (-0.3) signs; other signs neutral (+0.4).
    _friendly = {
        "sun": (["白羊座", "狮子座", "射手座"], ["天秤座", "水瓶座"]),
        "moon": (["金牛座", "巨蟹座", "双鱼座", "射手座"], ["摩羯座", "天蝎座"]),
        "mercury": (["双子座", "处女座"], ["射手座", "双鱼座"]),
        "venus": (["金牛座", "天秤座", "双鱼座"], ["白羊座", "天蝎座"]),
        "mars": (["白羊座", "天蝎座"], ["金牛座", "天秤座", "巨蟹座"]),
        "jupiter": (["射手座", "双鱼座", "巨蟹座"], ["双子座", "处女座", "摩羯座"]),
        "saturn": (["摩羯座", "水瓶座", "天秤座"], ["白羊座", "巨蟹座", "狮子座"]),
        "uranus": (["白羊座", "水瓶座", "射手座"], ("金牛座", "狮子座", "天蝎座")),
        "neptune": (["双鱼座", "射手座", "巨蟹座"], ("处女座", "双子座")),
    }
    _detrimental_pts = -0.3
    _neutral_pts = 0.4
    pos_by = {p["planet"]: p for p in positions}

    pts = 0.0
    breakdown: list[dict] = []
    for pl in primaries:
        pos = pos_by.get(pl)
        if not pos:
            continue
        friendly, detrimental = _friendly.get(pl, ([], []))
        if pos["sign"] in friendly:
            pts += 1.0
            breakdown.append({"planet": pl, "sign": pos["sign"], "match": "friendly", "pts": 1.0})
        elif pos["sign"] in detrimental:
            pts += _detrimental_pts
            breakdown.append({"planet": pl, "sign": pos["sign"], "match": "detrimental", "pts": _detrimental_pts})
        else:
            pts += _neutral_pts
            breakdown.append({"planet": pl, "sign": pos["sign"], "match": "neutral", "pts": _neutral_pts})
    # normalize: max primaries = 1.0, then apply sector weight
    normalized = min(pts / max(len(primaries), 1), 1.0) * weight
    normalized = min(normalized, 1.0)
    return normalized, breakdown


def _aspect_score(aspects: list[dict]) -> tuple[float, list[dict]]:
    """Score current aspects: trine/sextile positive, square/opposition negative."""
    pts = 0.0
    breakdown: list[dict] = []
    for a in aspects:
        if a["influence"] == "positive":
            pts += 0.15
            breakdown.append({"aspect": a, "effect": "+", "pts": 0.15})
        elif a["influence"] == "negative":
            pts -= 0.10
            breakdown.append({"aspect": a, "effect": "-", "pts": -0.10})
    # clamp 0..1
    return max(0.0, min(1.0, 0.5 + pts)), breakdown


def _transit_score(birth_iso: str | None, positions: list[dict]) -> tuple[float, list[dict]]:
    """Score transit hits to natal chart. None birth → 0.5 neutral."""
    if not birth_iso:
        return 0.5, [{"note": "no birth chart", "pts": 0.5}]
    transits = ephem.get_transits(birth_iso)
    if not transits:
        return 0.3, [{"note": "no transit triggers", "pts": 0.3}]
    pts = min(len(transits) / 20.0, 1.0)  # 20+ transits = full score
    return pts, [{"count": len(transits), "pts": pts}]


def _personal_score(birth_iso: str | None, ticker: str) -> tuple[float, list[dict]]:
    """Score personal fit: sector alignment with natal sun sign (MVP)."""
    if not birth_iso:
        return 0.5, [{"note": "no birth chart", "pts": 0.5}]
    natal = {p["planet"]: p for p in ephem.get_planet_positions(birth_iso)}
    natal_sun_sign = natal.get("sun", {}).get("sign")
    sector_key = sector_for(ticker)
    if not natal_sun_sign or not sector_key:
        return 0.5, [{"note": "missing natal sun or sector", "pts": 0.5}]

    # Map natal sun sign element to preferred sectors (MVP heuristic)
    _sign_to_sectors = {
        "白羊座": ["defense", "industrial", "ev"],
        "金牛座": ["finance", "consumer", "realestate"],
        "双子座": ["technology", "semiconductor"],
        "巨蟹座": ["consumer", "realestate"],
        "狮子座": ["technology", "semiconductor", "consumer"],
        "处女座": ["technology", "semiconductor", "finance"],
        "天秤座": ["finance", "consumer", "realestate"],
        "天蝎座": ["crypto", "defense", "energy"],
        "射手座": ["technology", "ev", "crypto"],
        "摩羯座": ["finance", "industrial", "energy"],
        "水瓶座": ["technology", "semiconductor", "crypto"],
        "双鱼座": ["energy", "crypto", "realestate"],
    }
    preferred = _sign_to_sectors.get(natal_sun_sign, [])
    pts = 1.0 if sector_key in preferred else 0.4
    return pts, [{"natal_sun": natal_sun_sign, "sector": sector_key, "pts": pts}]


# --- public API -------------------------------------------------------------

def compute_score(
    ticker: str,
    birth_iso: str | None = None,
    when_iso: str | None = None,
) -> dict:
    """Compute AstroScore 0-100 + breakdown + prediction direction.

    Returns dict matching AstroScoreOut schema.
    """
    positions = ephem.get_planet_positions(when_iso)
    aspects = ephem.get_aspects(when_iso)

    p_pts, p_br = _planetary_score(ticker, positions)
    a_pts, a_br = _aspect_score(aspects)
    t_pts, t_br = _transit_score(birth_iso, positions)
    f_pts, f_br = _personal_score(birth_iso, ticker)

    score = (
        p_pts * 40
        + a_pts * 30
        + t_pts * 20
        + f_pts * 10
    )
    score = round(score, 1)
    direction = direction_of(score)

    return {
        "ticker": ticker.upper(),
        "score": score,
        "direction": direction["direction"],
        "direction_label": direction["label"],
        "direction_emoji": direction["emoji"],
        "breakdown": {
            "planetary": round(p_pts * 40, 1),
            "aspect": round(a_pts * 30, 1),
            "transit": round(t_pts * 20, 1),
            "personal": round(f_pts * 10, 1),
        },
        "breakdown_detail": {
            "planetary": p_br,
            "aspect": a_br,
            "transit": t_br,
            "personal": f_br,
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def predict_7day(
    ticker: str,
    birth_iso: str | None = None,
) -> dict:
    """Stub 7-day prediction trend — MVP uses current score ± daily jitter.

    Real prediction (P2) will walk transits day-by-day; for now we synthesize
    7 bars from the current score with deterministic decay so the frontend can
    wire up the chart.
    """
    base = compute_score(ticker, birth_iso)
    s = base["score"]
    bars = []
    for i in range(7):
        # deterministic pseudo-confidence: high score → high confidence days
        conf = max(0, min(100, s - 5 + (i - 3) * 2 + (3 if i % 2 == 0 else -3)))
        bars.append({"day_offset": i, "confidence": round(conf, 1)})
    direction = direction_of(s)
    return {
        "ticker": ticker.upper(),
        "base_score": s,
        "direction": direction["direction"],
        "bars": bars,
        "note": "MVP stub — deterministic jitter, real prediction deferred to P2",
    }


# --- accuracy tracking (mock, persisted later) ------------------------------

_ACCURACY_MOCK = {
    "7d": {"correct": 86, "total": 100, "pct": 86.0},
    "30d": {"correct": 79, "total": 100, "pct": 79.0},
    "90d": {"correct": 74, "total": 100, "pct": 74.0},
    "all_time": {"correct": 1284, "total": 1500, "pct": 85.6},
}


def accuracy_for(ticker: str) -> dict:
    """Return mock historical accuracy — P2 will replace with DB-backed stats."""
    return {
        "ticker": ticker.upper(),
        "windows": _ACCURACY_MOCK,
        "note": "MVP mock — real rolling accuracy tracking in P2",
    }
