"""Swiss-style astronomy engine built on skyfield (offline via skyfield-data).

Design contract (kept tiny on purpose — MVP):
- All public functions return plain dicts matching the Pydantic schemas in app/schemas/.
- Positions are ecliptic longitude in degrees, mapped to the 12 zodiac signs.
- Aspects are computed pairwise among the 7 classical "lights" (Sun..Saturn) at a 10° orb
  for the major Ptolemaic aspects: conjunction 0°, opposition 180°, trine 120°, square 90°,
  sextile 60°.
- Moon phase derived from the Sun-Moon ecliptic longitude difference.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal

import skyfield_data
from skyfield.api import load_file, load

# --- ephemeris bootstrap (offline) -----------------------------------------

_BSP = os.path.join(os.path.dirname(skyfield_data.__file__), "data", "de421.bsp")
_PLANETS = [
    ("sun", "SUN"),
    ("moon", "MOON"),
    ("mercury", "MERCURY"),
    ("venus", "VENUS"),
    ("mars", "MARS"),
    ("jupiter", "JUPITER BARYCENTER"),
    ("saturn", "SATURN BARYCENTER"),
    ("uranus", "URANUS BARYCENTER"),
    ("neptune", "NEPTUNE BARYCENTER"),
]

# 12 zodiac signs, each spans 30° starting from 0° Aries.
_ZODIAC = [
    "白羊座", "金牛座", "双子座", "巨蟹座",
    "狮子座", "处女座", "天秤座", "天蝎座",
    "射手座", "摩羯座", "水瓶座", "双鱼座",
]
_ZODIAC_SYMBOL = [
    "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓",
]

AspectType = Literal["conjunction", "opposition", "trine", "square", "sextile"]
_ASPECTS: list[tuple[AspectType, float]] = [
    ("conjunction", 0.0),
    ("sextile", 60.0),
    ("square", 90.0),
    ("trine", 120.0),
    ("opposition", 180.0),
]
_ORB = 10.0  # degrees of tolerance


@lru_cache(maxsize=1)
def _eph() -> object:
    return load_file(_BSP)


@lru_cache(maxsize=1)
def _ts() -> object:
    return load.timescale()


def _resolve_time(ts, when_iso: str | None):
    """Build a skyfield Time from an ISO string, or now if None.

    skyfield rejects naive datetimes; if the string lacks tz/offset we treat it
    as UTC. Datetimes with explicit offset (e.g. `+08:00`) are honored.
    """
    if when_iso:
        dt = datetime.fromisoformat(when_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return ts.from_datetime(dt)
    return ts.now()


def _sign_of(lon_deg: float) -> tuple[str, str]:
    """Return (name, symbol) of the zodiac sign for an ecliptic longitude."""
    idx = int(lon_deg % 360 // 30) % 12
    return _ZODIAC[idx], _ZODIAC_SYMBOL[idx]


def _normalize(deg: float) -> float:
    return ((deg % 360) + 360) % 360


def _format_deg(deg: float) -> str:
    """e.g. 26.30° → `26°18'` (decimal → arc-minute string)."""
    whole = int(deg)
    minutes = int(round((deg - whole) * 60))
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{whole}°{minutes:02d}'"


# --- public API -------------------------------------------------------------

def get_planet_positions(when_iso: str | None = None) -> list[dict]:
    """Return current (or `when_iso`) ecliptic positions of all 9 planets.

    Output item shape:
        {planet, symbol, sign, sign_symbol, degree, degree_fmt, longitude, is_retrograde}
    """
    ts = _ts()
    t = _resolve_time(ts, when_iso)
    eph = _eph()
    earth = eph["earth"]

    out: list[dict] = []
    for short, key in _PLANETS:
        apparent = earth.at(t).observe(eph[key]).apparent()
        _lat, lon, _dist = apparent.ecliptic_latlon()
        lon_deg = _normalize(lon.degrees)
        sign, sym = _sign_of(lon_deg)
        symbol_map = {
            "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀",
            "mars": "♂", "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆",
        }
        # Retrograde: skyfield apparent motion is negative in ecliptic lon
        # over a 1-hour window — keep MVP simple, approximate via sign of delta.
        try:
            t2 = ts.tt_jd(t.tt + 1 / 24)
            lon2 = earth.at(t2).observe(eph[key]).apparent().ecliptic_latlon()[1].degrees
            retro = bool(lon2 < lon.degrees)
        except Exception:
            retro = False

        out.append({
            "planet": short,
            "symbol": symbol_map[short],
            "sign": sign,
            "sign_symbol": sym,
            "degree": float(round(lon_deg % 30, 2)),
            "degree_fmt": _format_deg(lon_deg % 30),
            "longitude": float(round(lon_deg, 2)),
            "is_retrograde": retro,
        })
    return out


def get_aspects(when_iso: str | None = None) -> list[dict]:
    """Return major aspects among Sun..Saturn (the 7 classical lights)."""
    ts = _ts()
    t = _resolve_time(ts, when_iso)
    eph = _eph()
    earth = eph["earth"]

    lons: dict[str, float] = {}
    for short, key in _PLANETS[:7]:  # Sun..Saturn
        lon = earth.at(t).observe(eph[key]).apparent().ecliptic_latlon()[1].degrees
        lons[short] = _normalize(lon)

    out: list[dict] = []
    pairs = [
        ("sun", "moon"), ("sun", "mercury"), ("sun", "venus"), ("sun", "mars"),
        ("sun", "jupiter"), ("sun", "saturn"), ("moon", "mercury"),
        ("moon", "venus"), ("moon", "mars"), ("moon", "jupiter"),
        ("moon", "saturn"), ("mercury", "venus"), ("mercury", "mars"),
        ("mercury", "jupiter"), ("mercury", "saturn"), ("venus", "mars"),
        ("venus", "jupiter"), ("venus", "saturn"), ("mars", "jupiter"),
        ("mars", "saturn"), ("jupiter", "saturn"),
    ]
    for p1, p2 in pairs:
        diff = _normalize(lons[p1] - lons[p2])
        if diff > 180:
            diff = 360 - diff
        for atype, target in _ASPECTS:
            orb = abs(diff - target)
            if orb <= _ORB:
                influence = "positive" if atype in ("trine", "sextile") else (
                    "neutral" if atype == "conjunction" else "negative"
                )
                out.append({
                    "planet1": p1, "planet2": p2,
                    "type": atype, "orb": float(round(orb, 2)),
                    "influence": influence,
                })
                break
    return out


def get_moon_phase(when_iso: str | None = None) -> dict:
    """Return moon phase name, illumination %, and angle from Sun-Moon lon diff."""
    ts = _ts()
    t = _resolve_time(ts, when_iso)
    eph = _eph()
    earth = eph["earth"]

    sun_lon = _normalize(
        earth.at(t).observe(eph["SUN"]).apparent().ecliptic_latlon()[1].degrees
    )
    moon_lon = _normalize(
        earth.at(t).observe(eph["MOON"]).apparent().ecliptic_latlon()[1].degrees
    )
    diff = _normalize(moon_lon - sun_lon)

    # Phase name lookup
    if diff < 22.5 or diff >= 337.5:
        name = "新月"
    elif diff < 67.5:
        name = "蛾眉月"
    elif diff < 112.5:
        name = "上弦月"
    elif diff < 157.5:
        name = "盈凸月"
    elif diff < 202.5:
        name = "满月"
    elif diff < 247.5:
        name = "亏凸月"
    elif diff < 292.5:
        name = "下弦月"
    else:
        name = "残月"

    illumination = float(round((1 - abs(diff - 180) / 180) * 100, 1))
    return {
        "name": name,
        "illumination_pct": illumination,
        "phase_angle": float(round(diff, 2)),
    }


def get_birth_chart(
    birth_iso: str,
    lat: float,
    lon: float,
) -> dict:
    """Compute a natal chart snapshot: planet positions + houses placeholder.

    For MVP we return ecliptic-longitude positions with sign/house computed via
    the equal-house system (each house = 30° starting from the ascendant, which
    we approximate as the ecliptic longitude of the eastern horizon). The proper
    Placidus house system needs topocentric computation and is deferred to P2.
    """
    positions = get_planet_positions(birth_iso)

    # Ascendant approximation: ecliptic longitude rising at birth lat / time.
    # Exact asc requires the local sidereal time; for MVP we use the Sun's
    # longitude offset by local hour angle as a rough estimate.
    ts = _ts()
    t = _resolve_time(ts, birth_iso)
    eph = _eph()
    earth = eph["earth"]
    sun_lon = _normalize(
        earth.at(t).observe(eph["SUN"]).apparent().ecliptic_latlon()[1].degrees
    )
    # Very rough local-hour approximation: shift by longitude/15° per hour of lon
    asc = _normalize(sun_lon + lon + 90)

    houses = []
    for i in range(12):
        cusp = _normalize(asc + i * 30)
        sign, sym = _sign_of(cusp)
        houses.append({"house": i + 1, "sign": sign, "cusp_deg": float(round(cusp, 2))})

    # Tag each planet with a house number (equal-house)
    for p in positions:
        p_lon = p["longitude"]
        for i in range(12):
            cusp = _normalize(asc + i * 30)
            next_cusp = _normalize(asc + (i + 1) * 30)
            in_house = cusp <= p_lon < next_cusp if cusp < next_cusp else (
                p_lon >= cusp or p_lon < next_cusp
            )
            if in_house:
                p["house"] = i + 1
                break

    return {
        "birth_iso": birth_iso,
        "latitude": lat,
        "longitude": lon,
        "ascendant_deg": float(round(asc, 2)),
        "ascendant_sign": _sign_of(asc),
        "houses": houses,
        "planets": positions,
        "aspects": get_aspects(birth_iso),
    }


def get_transits(
    birth_iso: str,
    when_iso: str | None = None,
) -> list[dict]:
    """Return transit-to-natal aspects — transiting planet hits natal longitude.

    For MVP we compute the angle between each current planet longitude and each
    natal planet longitude, flagging any major aspect within orb.
    """
    natal = {p["planet"]: p["longitude"] for p in get_planet_positions(birth_iso)}
    now_positions = get_planet_positions(when_iso)

    out: list[dict] = []
    for transiting in now_positions:
        t_lon = transiting["longitude"]
        for natal_planet, n_lon in natal.items():
            diff = _normalize(t_lon - n_lon)
            if diff > 180:
                diff = 360 - diff
            for atype, target in _ASPECTS:
                orb = abs(diff - target)
                if orb <= _ORB:
                    out.append({
                        "transiting_planet": transiting["planet"],
                        "natal_planet": natal_planet,
                        "type": atype,
                        "orb": float(round(orb, 2)),
                    })
                    break
    return out
