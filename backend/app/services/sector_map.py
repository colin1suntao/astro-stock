"""Sector → planet mapping. The scoring engine (P1-4) consumes this table to
weight planetary influence by sector. Hand-curated from the design doc §2.1.

Schema: sector_key → {primary_planets, weight}
- primary_planets: planets whose strength here is reinforced
- weight: relative emphasis multiplier (1.0 default, up to 1.5 for tight fit)
"""
SECTOR_PLANET_MAP: dict[str, dict] = {
    "technology": {
        "label": "科技 / AI",
        "primary_planets": ["uranus", "mercury", "sun"],
        "weight": 1.3,
    },
    "semiconductor": {
        "label": "半导体",
        "primary_planets": ["uranus", "mercury"],
        "weight": 1.3,
    },
    "defense": {
        "label": "军工 / 国防",
        "primary_planets": ["mars", "saturn"],
        "weight": 1.2,
    },
    "industrial": {
        "label": "工业 / 能源",
        "primary_planets": ["mars", "saturn"],
        "weight": 1.1,
    },
    "consumer": {
        "label": "消费零售",
        "primary_planets": ["venus", "sun"],
        "weight": 1.0,
    },
    "finance": {
        "label": "金融 / 奢侈品",
        "primary_planets": ["venus", "jupiter"],
        "weight": 1.2,
    },
    "energy": {
        "label": "能源 / 大宗",
        "primary_planets": ["neptune", "saturn"],
        "weight": 1.1,
    },
    "crypto": {
        "label": "加密货币",
        "primary_planets": ["neptune", "uranus", "pluto"],
        "weight": 1.4,
    },
    "ev": {
        "label": "电动车 / 新能源",
        "primary_planets": ["mars", "uranus"],
        "weight": 1.2,
    },
    "realestate": {
        "label": "房地产",
        "primary_planets": ["moon", "venus"],
        "weight": 1.0,
    },
}


# Ticker → sector_key. Stub for MVP; will later come from a fundamentals API.
TICKER_SECTOR: dict[str, str] = {
    "NVDA": "semiconductor",
    "AMD": "semiconductor",
    "AAPL": "technology",
    "TSLA": "ev",
    "PLTR": "technology",
    "META": "technology",
    "MSFT": "technology",
    "GOOGL": "technology",
    "LMT": "defense",
    "RTX": "defense",
    "JPM": "finance",
    "GS": "finance",
    "XOM": "energy",
    "CVX": "energy",
    "BTC": "crypto",
}


# A-share representatives per sector (Sina symbols: sh/sz + 6 digits).
# Used by /api/dashboard to avoid overseas HTTPS blocking on US tickers (P4-C).
A_SHARE_REPS: dict[str, dict[str, str]] = {
    "technology": {"symbol": "sz000063", "ticker": "ZTE", "name": "中兴通讯"},
    "semiconductor": {"symbol": "sh688981", "ticker": "SMIC", "name": "中芯国际"},
    "defense": {"symbol": "sh600150", "ticker": "AVIC", "name": "中航沈飞"},
    "industrial": {"symbol": "sh601857", "ticker": "PETRO", "name": "中国石油"},
    "consumer": {"symbol": "sh600519", "ticker": "MOUTAI", "name": "贵州茅台"},
    "finance": {"symbol": "sh601318", "ticker": "PINGAN", "name": "中国平安"},
    "energy": {"symbol": "sh600028", "ticker": "SINOPEC", "name": "中国石化"},
    "crypto": {"symbol": "sz002230", "ticker": "LEBOND", "name": "科大讯飞"},
    "ev": {"symbol": "sz002594", "ticker": "BYD", "name": "比亚迪"},
    "realestate": {"symbol": "sz000002", "ticker": "VANKE", "name": "万科A"},
}


def sector_for(ticker: str) -> str | None:
    """Return sector_key for a ticker, or None if unknown."""
    return TICKER_SECTOR.get(ticker.upper())


def sector_label(sector_key: str | None) -> str:
    if not sector_key:
        return "未知板块"
    return SECTOR_PLANET_MAP.get(sector_key, {}).get("label", sector_key)
