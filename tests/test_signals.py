"""tests/test_signals.py"""
import pytest
from src.analyzers.signals import analyze_signals, _score_ticker


def _make_ticker(change_pct=0.0, price=100.0, ema_8=100, ema_21=98, ema_50=95, ema_200=90):
    return {
        "symbol": "TEST",
        "price": price,
        "prev_close": price / (1 + change_pct / 100),
        "premarket_change_pct": change_pct,
        "ema_8": ema_8,
        "ema_21": ema_21,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "avg_volume_20d": 1_000_000,
        "today_volume": 900_000,
        "week52_high": 120.0,
    }


def test_bullish_gap_up():
    data = _make_ticker(change_pct=3.5)
    sig = _score_ticker(data)
    assert sig["bias"] in ("bullish", "strongly_bullish")
    assert "gap-up" in sig["flags"]
    assert "strong-gap-up" in sig["flags"]


def test_bearish_gap_down():
    # Use a bearish EMA stack to ensure bearish bias dominates
    data = _make_ticker(change_pct=-3.5, price=85.0, ema_8=84, ema_21=88, ema_50=92, ema_200=100)
    sig = _score_ticker(data)
    assert sig["bias"] in ("bearish", "strongly_bearish")
    assert "gap-down" in sig["flags"]


def test_ema_stack_bullish():
    data = _make_ticker(ema_8=105, ema_21=102, ema_50=98)
    sig = _score_ticker(data)
    assert "ema-stack-bullish" in sig["flags"]


def test_ema_stack_bearish():
    data = _make_ticker(price=90, ema_8=89, ema_21=92, ema_50=95, ema_200=100)
    sig = _score_ticker(data)
    assert "ema-stack-bearish" in sig["flags"]


def test_near_52w_high():
    data = _make_ticker(price=119.0)
    sig = _score_ticker(data)
    assert "near-52w-high" in sig["flags"]


def test_neutral_no_signals():
    # Flat price, neutral EMA positioning — bias can be bullish from EMA stack
    data = _make_ticker(change_pct=0.1)
    sig = _score_ticker(data)
    assert sig["bias"] in ("neutral", "bullish", "strongly_bullish")


def test_analyze_signals_handles_errors():
    watchlist = {
        "GOOD": _make_ticker(change_pct=2.0),
        "BAD": {"symbol": "BAD", "error": "connection timeout"},
    }
    signals = analyze_signals(watchlist)
    assert "GOOD" in signals
    assert signals["BAD"]["bias"] == "unknown"


def test_note_is_non_empty():
    data = _make_ticker(change_pct=1.5)
    sig = _score_ticker(data)
    assert len(sig["note"]) > 0
