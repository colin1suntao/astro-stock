"""LLM interpretation — LongCat-2.0 (OpenAI-compatible endpoint).

Astrologer persona + current celestial JSON → natural-language reading.
LongCat-2.0 is a reasoning model: output lives in choices[0].message.content
(after reasoning_content), so we pull from there and give generous max_tokens.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.services import ephem, scoring
from app.services.sector_map import sector_for, sector_label


_SYSTEM_PROMPT = """你是一位融合占星学与投资分析的「星象投资顾问」，声音沉静而富有洞察力。

你的任务：根据当下的行星位置、相位、板块映射，给出一段简短而具体的中文解读，
帮助投资者理解天象对某板块或个股的倾向。规则：
- 用 2-4 句话讲清「核心天象 + 对应板块影响 + 操作倾向」。
- 可以提具体行星和星座，但避免堆砌术语，要让普通人懂。
- 明确区分「和谐助力」与「张力警示」，不要模棱两可。
- 不保证收益，结尾一句风险提示：「天象仅供参考，投资决策请结合基本面。」
- 不要罗列所有行星，只挑与本话题最相关的 1-2 颗。
- 严禁Markdown、严禁英文、严禁表情符、严禁开头加「好的」之类客套。
- 直接输出解读正文，不要推理过程外露。"""


def _build_user_prompt(topic: str, ticker: str | None, birth_iso: str | None) -> str:
    """Assemble the celestial context JSON + user question."""
    now_iso = datetime.now(timezone.utc).isoformat()
    positions = ephem.get_planet_positions(now_iso)
    aspects = ephem.get_aspects(now_iso)
    moon = ephem.get_moon_phase(now_iso)

    ctx = {
        "topic": topic,
        "now_utc": now_iso,
        "moon": {"name": moon["name"], "illumination_pct": moon["illumination_pct"]},
        "positions": [{"planet": p["planet"], "sign": p["sign"], "degree": p["degree"],
                        "retrograde": bool(p["is_retrograde"])} for p in positions],
        "aspects": [{"p1": a["planet1"], "p2": a["planet2"], "type": a["type"],
                      "influence": a["influence"]} for a in aspects],
    }
    if ticker:
        ctx["ticker"] = ticker.upper()
        ctx["sector"] = sector_for(ticker)
        ctx["sector_label"] = sector_label(ctx["sector"])
        score = scoring.compute_score(ticker, birth_iso=birth_iso, when_iso=now_iso)
        ctx["astro_score"] = {"score": score["score"], "direction": score["direction"],
                              "breakdown": score["breakdown"]}

    return f"当前天象 JSON:\n{json.dumps(ctx, ensure_ascii=False, indent=2)}\n\n请就「{topic}」给出解读。"


def interpret(topic: str, ticker: str | None = None, birth_iso: str | None = None) -> dict:
    """Call LongCat for a natural-language reading. Returns {text, model, tokens}."""
    user_prompt = _build_user_prompt(topic, ticker, birth_iso)
    try:
        r = httpx.post(
            settings.llm_base_url,
            timeout=120,
            headers={"Authorization": f"Bearer {settings.llm_api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": settings.llm_max_tokens,
            },
        )
        r.raise_for_status()
        d = r.json()
        # LongCat-2.0: body lives in choices[0].message.content (post-reasoning)
        text = (d.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
        usage = d.get("usage", {})
        return {
            "text": text.strip() or "（模型未返回正文，请稍后重试）",
            "model": d.get("model", settings.llm_model),
            "tokens": usage.get("total_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "topic": topic,
            "ticker": ticker.upper() if ticker else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.HTTPError as e:
        return {"text": f"❌ LLM 调用失败: {type(e).__name__}", "model": settings.llm_model,
                "tokens": None, "topic": topic, "ticker": ticker.upper() if ticker else None,
                "generated_at": datetime.now(timezone.utc).isoformat()}
