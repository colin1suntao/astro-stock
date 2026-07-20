"""Backtest engine — score vs actual price move.

P3-1: real-data path via Sina A-share K-line (`a_share_symbol`). The engine
walks bars, computes score at each bar's date, compares to next-bar move.
scipy.optimize regression tunes the 4 scoring weights against backtest residuals.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import ephem, market, scoring


# --- real-data backtest (P3-1b) ---------------------------------------------

def _real_backtest_sample(a_symbol: str, datalen: int = 60) -> list[dict]:
    """Walk Sina A-share bars; for each bar compute score at bar.date, compare
    to next-bar's pct move. Returns list of {date, score, predicted_direction,
    actual_pct, correct}.

    Note: ephem uses the bar's date to compute planet positions AT that date,
    so this is a true historical walk (not reusing today's positions).
    """
    bars = market.get_a_share_history(a_symbol, datalen + 1)
    if len(bars) < 2:
        return []
    out: list[dict] = []
    for i in range(len(bars) - 1):
        bar = bars[i]
        nxt = bars[i + 1]
        # score at bar's date (use close date as the "when")
        when_iso = f"{bar['date']}T15:00:00+08:00"  # A-share close ~15:00 CST
        try:
            s = scoring.compute_score(a_symbol, when_iso=when_iso)
            score = s["score"]
            direction = s["direction"]
        except Exception:
            continue
        actual_pct = round((nxt["close"] - bar["close"]) / bar["close"] * 100, 2)
        if direction == "neutral":
            correct = None
        elif direction == "bull":
            correct = actual_pct >= 0
        else:
            correct = actual_pct < 0
        out.append({
            "date": bar["date"],
            "score": float(score),
            "breakdown": s.get("breakdown", {}),  # P4-T2: per-bar components for real regression
            "predicted_direction": direction,
            "actual_pct": actual_pct,
            "correct": correct,
        })
    return out


def _mock_backtest_sample(ticker: str, days: int = 60) -> list[dict]:
    """Synthetic sample for pipeline validation when no real data source."""
    out: list[dict] = []
    base = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for i in range(days):
        d = base + timedelta(days=i)
        score = round(50 + 15 * (i / 4 % 2 - 1) * (-1) ** i + (3 if i % 7 == 0 else -3), 1)
        score = max(20, min(95, score))
        actual_pct = round((score - 50) / 5 + ((i * 7) % 5 - 2), 2)
        direction = scoring.direction_of(score)["direction"]
        if direction == "neutral":
            correct = None
        elif direction == "bull":
            correct = actual_pct >= 0
        else:
            correct = actual_pct < 0
        out.append({"date": d.date().isoformat(), "score": score,
                    "predicted_direction": direction, "actual_pct": actual_pct,
                    "correct": correct})
    return out


# --- public API --------------------------------------------------------------

def run_backtest(
    ticker: str,
    days: int = 60,
    use_mock: bool = True,
    a_share_symbol: str | None = None,
) -> dict:
    """Run backtest. Mock path (default) for pipeline validation; real path
    via `a_share_symbol` (e.g. 'sh600519') hits Sina K-line.

    `ticker` is used as the scoring key (sector lookup); for A-share backtest
    pass the A-share code as `a_share_symbol` and a US-equivalent sector ticker
    as `ticker` (e.g. ticker='NVDA', a_share_symbol='sz000001' for 「半导体」).
    """
    if use_mock or not a_share_symbol:
        bars = _mock_backtest_sample(ticker, days)
        data_source = "mock"
    else:
        bars = _real_backtest_sample(a_share_symbol, days)
        data_source = f"sina:{a_share_symbol}"
        _persist_bars(a_share_symbol, bars)  # P4-T3: per-bar breakdown DB 持久化

    scored = [b for b in bars if b["correct"] is not None]
    correct_n = sum(1 for b in scored if b["correct"])
    accuracy = round(correct_n / max(len(scored), 1) * 100, 1)

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
        "a_share_symbol": a_share_symbol,
        "days": days,
        "data_source": data_source,
        "overall_accuracy": accuracy,
        "scored_count": len(scored),
        "neutral_count": len(bars) - len(scored),
        "by_direction": by_dir,
        "sample_bars": bars,        # P4-T2: return ALL bars (not [:10]) so tune_weights has full data
        "sample_bars_preview": bars[:10],  # keep a small preview for UI display
    }


def recommend_weight_adjustments(backtest_result: dict) -> list[dict]:
    """P2-2b heuristic: suggest tweaks based on per-direction accuracy."""
    recs: list[dict] = []
    by_d = backtest_result["by_direction"]
    bull_acc = by_d.get("bull", {}).get("accuracy", 100)
    bear_acc = by_d.get("bear", {}).get("accuracy", 100)

    if bull_acc < 60:
        recs.append({"issue": "bull predictions under 60% accuracy",
                     "fix": "raise planetary weight from 40 → 45; friendly-sign match stricter"})
    if bear_acc < 60:
        recs.append({"issue": "bear predictions under 60% accuracy",
                     "fix": "raise aspect negative penalty from -0.10 → -0.15"})
    if not recs:
        recs.append({"issue": "none", "fix": "weights look healthy — no adjustment needed"})
    return recs


# --- scipy weight regression (P3-1c) ----------------------------------------

# Current scoring weights: Score = planetary×40 + aspect×30 + transit×20 + personal×10
_CURRENT_WEIGHTS = [40.0, 30.0, 20.0, 10.0]


def _persist_bars(a_share_symbol: str, bars: list[dict]) -> None:
    """P4-T3: persist per-bar breakdown to DB (BacktestBar table).

    Idempotent: skips bars already stored for (symbol, date) to avoid dup on rerun.
    """
    import json
    from app.db import SessionLocal
    from app.models import BacktestBar
    from sqlalchemy import select

    if not bars:
        return
    db = SessionLocal()
    try:
        existing = set(db.scalars(
            select(BacktestBar.date).where(BacktestBar.a_share_symbol == a_share_symbol)
        ).all())
        for b in bars:
            if b.get("date") in existing:
                continue
            db.add(BacktestBar(
                a_share_symbol=a_share_symbol,
                date=b.get("date", ""),
                score=float(b.get("score", 0.0)),
                predicted_direction=b.get("predicted_direction", "neutral"),
                actual_pct=float(b.get("actual_pct", 0.0)),
                correct=b.get("correct"),
                breakdown_json=json.dumps(b.get("breakdown", {}), ensure_ascii=False),
            ))
        db.commit()
    finally:
        db.close()


def tune_weights(backtest_results: list[dict]) -> dict:
    """Use scipy.optimize to find weights minimizing prediction error.

    Input: list of `run_backtest` results (each with sample_bars containing
    {score, actual_pct, correct}). Aggregates all bars, then minimizes the
    total misprediction count across all results by reweighting.

    Returns {original, tuned, improvement_pct, bars_used}.
    """
    from scipy.optimize import minimize  # local import — scipy optional at runtime

    # Flatten all scored bars into (breakdown_components, actual_correct) pairs.
    # We reconstruct breakdown components from score vs current weights.
    # Since sample_bars only has aggregate score, we approximate: optimize the
    # 4 weights so that score-direction best matches actual sign.
    all_bars: list[dict] = []
    for r in backtest_results:
        for b in r.get("sample_bars", []):
            if b.get("correct") is not None:
                all_bars.append(b)

    if len(all_bars) < 5:
        return {"original": _CURRENT_WEIGHTS, "tuned": _CURRENT_WEIGHTS,
                "improvement_pct": 0.0, "bars_used": len(all_bars),
                "note": "insufficient bars (<5) for regression"}

    def _misclassification_count(weights: list[float]) -> float:
        """For given weights, recompute score direction and count wrong predictions.

        P4-T2: now we have per-bar breakdown components stored, so recompute the
        score as a true weighted sum of components rather than a rescale proxy.
        """
        w_planetary, w_aspect, w_transit, w_personal = weights
        wrong = 0.0
        for b in all_bars:
            br = b.get("breakbreak") or b.get("breakdown") or {}
            p = br.get("planetary", 0.0)
            a = br.get("aspect", 0.0)
            t = br.get("transit", 0.0)
            f = br.get("personal", 0.0)
            new_score = p * w_planetary + a * w_aspect + t * w_transit + f * w_personal
            new_dir = scoring.direction_of(new_score)["direction"]
            if new_dir == "neutral":
                continue
            actual_pos = b["actual_pct"] >= 0
            pred_pos = new_dir == "bull"
            if actual_pos != pred_pos:
                wrong += 1.0
        return wrong

    from scipy.optimize import differential_evolution  # global search beats Nelder-Mead on step landscape

    bounds = [(0.0, 60.0)] * 4  # each weight in [0, 60] (originals sum to 100)
    result = differential_evolution(
        _misclassification_count, bounds,
        seed=42, maxiter=60, tol=1e-3, polish=True, init='sobol',
    )
    tuned = [round(float(w), 1) for w in result.x.tolist()]
    orig_wrong = _misclassification_count(_CURRENT_WEIGHTS)
    tuned_wrong = _misclassification_count(result.x)
    improvement = round((orig_wrong - tuned_wrong) / max(len(all_bars), 1) * 100, 1)

    return {
        "original": _CURRENT_WEIGHTS,
        "tuned": tuned,
        "improvement_pct": improvement,
        "bars_used": len(all_bars),
        "original_wrong": int(orig_wrong),
        "tuned_wrong": int(tuned_wrong),
    }
