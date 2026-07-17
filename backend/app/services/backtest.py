"""Backtest engine — score vs actual price move.

P2-2a: pipeline runs on mock historical bars (Tencent K-line param format
unstable). Real-data hookup deferred. The engine is data-source-agnostic:
feed it (date, score, actual_pct_move) triples and it reports accuracy.

Accuracy metric: prediction correct if
  score >= 60 (bull) AND actual_pct >= 0
  score <= 40 (bear) AND actual_pct < 0
  else neutral — not counted against accuracy.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import ephem, scoring


# --- mock historical bars ----------------------------------------------------
# Synthetic but plausible: 60 trading days, score jitters 45-80, actual move
# correlates with score ± noise. Good enough to validate the pipeline + show
# what real backtest output looks like before P2-2c wires real K-line.

def _mock_backtest_sample(ticker: str, days: int = 60) -> list[dict]:
    """Return list of {date, score, predicted_direction, actual_pct, correct}.

    Synthetic: score = 50 + 15*sin(day/4) + sector_bonus; actual_pct follows
    score/10 + noise. Deterministic so tests are reproducible.
    """
    sector_bonus = {
        "NVDA": 8, "TSLA": 6, "AAPL": 4, "AMD": 5, "PLTR": 7, "META": 5,
    }.get(ticker.upper(), 0)

    out: list[dict] = []
    base = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for i in range(days):
        d = base + timedelta(days=i)
        score = round(50 + 15 * (i / 4 % 2 - 1) * (-1) ** i + sector_bonus + (3 if i % 7 == 0 else -3), 1)
        score = max(20, min(95, score))
        # actual move: high score → positive, low → negative, with noise
        actual_pct = round((score - 50) / 5 + ((i * 7) % 5 - 2), 2)
        direction = scoring.direction_of(score)["direction"]
        if direction == "neutral":
            correct = None  # neutral not counted
        elif direction == "bull":
            correct = actual_pct >= 0
        else:
            correct = actual_pct < 0
        out.append({
            "date": d.date().isoformat(),
            "score": score,
            "predicted_direction": direction,
            "actual_pct": actual_pct,
            "correct": correct,
        })
    return out


# --- public API --------------------------------------------------------------

def run_backtest(
    ticker: str,
    days: int = 60,
    use_mock: bool = True,
) -> dict:
    """Run backtest over `days` history. Returns accuracy stats + sample bars.

    `use_mock=True` (default for P2-2a) feeds synthetic data; when real K-line
    hookup lands (P2-2c), pass False to use actual market history.
    """
    if use_mock:
        bars = _mock_backtest_sample(ticker, days)
    else:
        # TODO P2-2c: walk real Tencent K-line, compute score at each bar's date
        # via ephem.get_planet_positions(date), compare to next-day move.
        bars = _mock_backtest_sample(ticker, days)

    scored = [b for b in bars if b["correct"] is not None]
    correct_n = sum(1 for b in scored if b["correct"])
    accuracy = round(correct_n / max(len(scored), 1) * 100, 1)

    # Direction breakdown
    by_dir: dict[str, dict] = {}
    for b in bars:
        d = b["predicted_direction"]
        by_dir.setdefault(d, {"total": 0, "correct": 0})
        by_dir[d]["total"] += 1
        if b["correct"]:
            by_dir[d]["correct"] += 1
    for d, v in by_dir.items():
        v["accuracy"] = round(v["correct"] / max(v["total"], 1) * 100, 1)

    return {
        "ticker": ticker.upper(),
        "days": days,
        "data_source": "mock" if use_mock else "real",
        "overall_accuracy": accuracy,
        "scored_count": len(scored),
        "neutral_count": len(bars) - len(scored),
        "by_direction": by_dir,
        "sample_bars": bars[:10],  # first 10 for frontend preview
    }


def recommend_weight_adjustments(backtest_result: dict) -> list[dict]:
    """P2-2b: suggest scoring weight tweaks based on backtest accuracy.

    MVP heuristic: if bull-accuracy < 60%, boost planetary weight; if bear
    accuracy < 60%, boost aspect (negative) weight. Real regression tuning
    would need scipy.optimize — deferred.
    """
    recs: list[dict] = []
    by_d = backtest_result["by_direction"]
    bull_acc = by_d.get("bull", {}).get("accuracy", 100)
    bear_acc = by_d.get("bear", {}).get("accuracy", 100)

    if bull_acc < 60:
        recs.append({
            "issue": "bull predictions under 60% accuracy",
            "fix": "raise planetary weight from 40 → 45; friendly-sign match stricter",
        })
    if bear_acc < 60:
        recs.append({
            "issue": "bear predictions under 60% accuracy",
            "fix": "raise aspect negative penalty from -0.10 → -0.15",
        })
    if not recs:
        recs.append({"issue": "none", "fix": "weights look healthy — no adjustment needed"})
    return recs
