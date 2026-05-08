"""
analyzers/signals.py

Generates trading signals for each ticker based on pre-market data.
Logic mirrors common scan criteria: gap conditions, EMA positioning,
volume relative to average, and proximity to key levels.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)

# Thresholds
GAP_UP_THRESHOLD = 1.0      # % above prev close = gap up
GAP_DOWN_THRESHOLD = -1.0   # % below prev close = gap down
HIGH_VOLUME_MULTIPLIER = 1.5


def analyze_signals(watchlist_data: dict[str, Any]) -> dict[str, Any]:
    """
    For each ticker in watchlist_data, generate a signal dict.
    Returns a dict keyed by ticker.
    """
    signals = {}

    for symbol, data in watchlist_data.items():
        if "error" in data:
            signals[symbol] = {"bias": "unknown", "note": "data unavailable", "flags": []}
            continue

        try:
            signals[symbol] = _score_ticker(data)
        except Exception as e:
            log.warning(f"Signal generation failed for {symbol}: {e}")
            signals[symbol] = {"bias": "unknown", "note": "analysis error", "flags": []}

    return signals


def _score_ticker(data: dict) -> dict:
    """Score a single ticker and return signal dict."""
    flags = []
    bias_score = 0  # positive = bullish, negative = bearish

    price = data.get("price")
    prev_close = data.get("prev_close")
    change_pct = data.get("premarket_change_pct", 0) or 0
    ema_8 = data.get("ema_8")
    ema_21 = data.get("ema_21")
    ema_50 = data.get("ema_50")
    ema_200 = data.get("ema_200")
    avg_vol = data.get("avg_volume_20d")
    today_vol = data.get("today_volume")
    week52_high = data.get("week52_high")

    # ── Gap Analysis ──────────────────────────────────────────────────────────
    if change_pct >= GAP_UP_THRESHOLD:
        flags.append("gap-up")
        bias_score += 1
        if change_pct >= 3.0:
            flags.append("strong-gap-up")
            bias_score += 1
    elif change_pct <= GAP_DOWN_THRESHOLD:
        flags.append("gap-down")
        bias_score -= 1
        if change_pct <= -3.0:
            flags.append("strong-gap-down")
            bias_score -= 1

    # ── EMA Positioning ───────────────────────────────────────────────────────
    if price and ema_50:
        if price > ema_50:
            flags.append("above-50ema")
            bias_score += 1
        else:
            flags.append("below-50ema")
            bias_score -= 1

    if price and ema_200:
        if price > ema_200:
            flags.append("above-200ema")
            bias_score += 1
        else:
            flags.append("below-200ema")
            bias_score -= 1

    if ema_8 and ema_21 and ema_50:
        if ema_8 > ema_21 > ema_50:
            flags.append("ema-stack-bullish")
            bias_score += 2
        elif ema_8 < ema_21 < ema_50:
            flags.append("ema-stack-bearish")
            bias_score -= 2

    # ── Volume ────────────────────────────────────────────────────────────────
    if avg_vol and today_vol:
        vol_ratio = today_vol / avg_vol
        if vol_ratio >= HIGH_VOLUME_MULTIPLIER:
            flags.append(f"high-volume-{vol_ratio:.1f}x")
            # Volume amplifies direction
            bias_score += 1 if bias_score > 0 else -1

    # ── 52-Week High Proximity ────────────────────────────────────────────────
    if price and week52_high:
        pct_from_high = ((week52_high - price) / week52_high) * 100
        if pct_from_high <= 2.0:
            flags.append("near-52w-high")
            bias_score += 1
        elif pct_from_high >= 25.0:
            flags.append("deep-drawdown")
            bias_score -= 1

    # ── Bias Label ────────────────────────────────────────────────────────────
    if bias_score >= 3:
        bias = "strongly_bullish"
    elif bias_score >= 1:
        bias = "bullish"
    elif bias_score <= -3:
        bias = "strongly_bearish"
    elif bias_score <= -1:
        bias = "bearish"
    else:
        bias = "neutral"

    note = _generate_note(flags, change_pct, bias)

    return {
        "bias": bias,
        "bias_score": bias_score,
        "flags": flags,
        "note": note,
        "change_pct": change_pct,
    }


def _generate_note(flags: list[str], change_pct: float, bias: str) -> str:
    """Generate a human-readable one-liner for the brief."""
    parts = []

    if "gap-up" in flags:
        parts.append(f"Gap-up {change_pct:+.1f}%")
    elif "gap-down" in flags:
        parts.append(f"Gap-down {change_pct:+.1f}%")
    else:
        parts.append(f"Flat open {change_pct:+.1f}%")

    if "ema-stack-bullish" in flags:
        parts.append("EMA stack bullish")
    elif "ema-stack-bearish" in flags:
        parts.append("EMA stack bearish")
    elif "above-50ema" in flags:
        parts.append("Above 50 EMA")
    elif "below-50ema" in flags:
        parts.append("Below 50 EMA")

    if any("high-volume" in f for f in flags):
        parts.append("elevated volume")

    if "near-52w-high" in flags:
        parts.append("near 52w high")

    return " | ".join(parts)
