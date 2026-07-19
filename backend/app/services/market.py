"""Market data client — Sina (real-time) + Tencent ifzq (history K-line).

Source selection was empirical:
- yfinance / Yahoo / Alpha Vantage / Stooq all blocked by network TLS拦截 to overseas HTTPS.
- Sina `hq.sinajs.cn/list=gb_<sym>` — reachable, GBK-encoded, single-symbol per call
  (multi-symbol list sometimes 403), stable at ~0.3s spacing.
- Tencent `web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=us<sym>,day,start,end,count,qfq`
  — reachable, JSON, returns OHLCV daily bars.

Field maps (verified 2026-07-16 against NVDA):
  Sina payload[0..35]:
    [0] name  [1] price  [2] chg_pct  [4] chg  [5] prev_close
    [6] open  [7] day_high  [8] 52w_high  [9] 52w_low
    [10] volume  [12] market_cap  [13] pe  [26] prev_day_close
  Tencent kline day bar: [date, open, close, high, low, volume]
"""
from __future__ import annotations

import json
import re
import time
from functools import lru_cache

import httpx

_SINA = "https://hq.sinajs.cn/list=gb_{sym}"
_SINA_A = "https://hq.sinajs.cn/list={sym}"  # A-share realtime, GBK
_SINA_HEADERS = {"Referer": "https://finance.sina.com.cn/"}
_SINA_KLINE = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
    "/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}"
)
_TENCENT = (
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    "?_var=kline_dayq&param=us{sym},day,{start},{end},{count},qfq"
)
_TIMEOUT = 12
_RETRIES = 3
_RETRY_DELAY = 0.4


def _retry_get(url: str, headers: dict | None = None) -> httpx.Response:
    last: Exception | None = None
    for _ in range(_RETRIES):
        try:
            r = httpx.get(url, timeout=_TIMEOUT, headers=headers or {}, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 20:
                return r
        except (httpx.HTTPError, httpx.TransportError) as e:
            last = e
        time.sleep(_RETRY_DELAY)
    raise RuntimeError(f"fetch failed after {_RETRIES} retries: {last}")


def _parse_sina(payload: str) -> dict:
    """Parse one Sina `gb_*` line into a quote dict. Empty payload → empty dict."""
    # var hq_str_gb_nvda="英伟达,212.5,...";
    m = re.search(r'"([^"]*)"', payload)
    if not m or not m.group(1):
        return {}
    fields = m.group(1).split(",")
    if len(fields) < 27:
        return {}
    return {
        "ticker": payload.split("=")[0].split("_")[-1].strip(),
        "name": fields[0],
        "price": float(fields[1] or 0),
        "change_pct": float(fields[2] or 0),
        "change": float(fields[4] or 0),
        "prev_close": float(fields[5] or 0),
        "open": float(fields[6] or 0),
        "day_high": float(fields[7] or 0),
        "52w_high": float(fields[8] or 0),
        "52w_low": float(fields[9] or 0),
        "volume": int(float(fields[10] or 0)),
        "market_cap": float(fields[12] or 0),
        "pe": float(fields[13] or 0),
        "prev_day_close": float(fields[26] or 0),
        "fetched_at": fields[3] if len(fields) > 3 else "",
    }


def get_quote(ticker: str) -> dict:
    """Return real-time quote for a US ticker (e.g. 'NVDA'). Empty dict on miss."""
    url = _SINA.format(sym=ticker.lower())
    r = _retry_get(url, _SINA_HEADERS)
    r.encoding = "gbk"
    return _parse_sina(r.text)


def _parse_sina_a(payload: str, symbol: str) -> dict:
    """Parse one Sina A-share line (hq.sinajs.cn/list=sh600519) into a quote dict.

    A-share payload CSV differs from US:
      [0] name  [1] open  [2] prev_close  [3] price
      [4] day_high  [5] day_low  [6] bid1  [7] ask1
      [8] volume_shares  [9] amount_wan  [30] date  [31] time
    """
    m = re.search(r'"([^"]*)"', payload)
    if not m or not m.group(1):
        return {}
    fields = m.group(1).split(",")
    if len(fields) < 32:
        return {}
    name = fields[0]
    open_v = float(fields[1] or 0)
    prev_close = float(fields[2] or 0)
    price = float(fields[3] or 0)
    change = price - prev_close if prev_close else 0.0
    change_pct = (change / prev_close * 100) if prev_close else 0.0
    return {
        "ticker": symbol.upper(),
        "name": name,
        "price": price,
        "change_pct": round(change_pct, 2),
        "change": round(change, 2),
        "prev_close": prev_close,
        "open": open_v,
        "day_high": float(fields[4] or 0),
        "52w_high": 0.0,  # A-share payload lacks 52w; leave 0
        "52w_low": 0.0,
        "volume": int(float(fields[8] or 0)),
        "market_cap": 0.0,
        "pe": 0.0,
        "prev_day_close": prev_close,
        "fetched_at": f"{fields[30]} {fields[31]}" if len(fields) > 31 else "",
    }


def get_a_share_quote(symbol: str) -> dict:
    """Real-time A-share quote via Sina (真源, P4-C). Empty dict on miss.

    `symbol` uses Sina prefix: sh/sz + 6 digits (e.g. 'sh600519' 贵州茅台).
    """
    url = _SINA_A.format(sym=symbol)
    r = _retry_get(url, _SINA_HEADERS)
    r.encoding = "gbk"
    return _parse_sina_a(r.text, symbol)


def get_history(
    ticker: str,
    count: int = 30,
    start: str = "",
    end: str = "",
) -> list[dict]:
    """Return daily OHLCV bars. Dates `YYYY-MM-DD`; empty list on failure.

    `start`/`end` optional; when both empty the API returns the most recent
    `count` bars ending today.
    """
    url = _TENCENT.format(
        sym=ticker.upper(),
        start=start,
        end=end,
        count=int(count),
    )
    r = _retry_get(url)
    # body: kline_dayq={"code":0,...,"data":{"usNVDA":{"day":[["2026-07-15","211.96",...]]}}}
    body = r.text
    body = body[body.index("=") + 1 :] if body.startswith("kline_dayq=") else body
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        return []
    if doc.get("code") != 0:
        return []
    bars = doc.get("data", {}).get(f"us{ticker.upper()}", {}).get("day", [])
    out: list[dict] = []
    for b in bars:
        if len(b) < 6:
            continue
        out.append({
            "date": b[0],
            "open": float(b[1] or 0),
            "close": float(b[2] or 0),
            "high": float(b[3] or 0),
            "low": float(b[4] or 0),
            "volume": int(float(b[5] or 0)),
        })
    return out


def get_a_share_history(symbol: str, datalen: int = 60) -> list[dict]:
    """Fetch A-share / index daily bars from Sina (真源, P3-1).

    `symbol` uses Sina prefix: sh/sz + 6 digits (e.g. 'sh600519' 贵州茅台,
    'sz000001' 平安银行, 'sz399001' 深证成指). Returns most recent `datalen`
    bars ascending. Empty list on failure.
    """
    url = _SINA_KLINE.format(sym=symbol, n=int(datalen))
    r = _retry_get(url)
    try:
        bars = json.loads(r.text)
    except json.JSONDecodeError:
        return []
    if not isinstance(bars, list):
        return []
    out: list[dict] = []
    for b in bars:
        if not isinstance(b, dict) or "day" not in b:
            continue
        out.append({
            "date": b["day"],
            "open": float(b.get("open") or 0),
            "close": float(b.get("close") or 0),
            "high": float(b.get("high") or 0),
            "low": float(b.get("low") or 0),
            "volume": int(float(b.get("volume") or 0)),
        })
    return out
