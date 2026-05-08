"""tests/test_brief.py"""
import pytest
from src.formatters.brief import assemble_brief, _format_watchlist


MOCK_FUTURES = {
    "futures": {
        "S&P 500 Futures": {"price": 5500.0, "change_pct": 0.35, "direction": "▲"},
        "VIX": {"price": 17.2, "change_pct": -2.1, "direction": "▼"},
    },
    "sectors": {
        "XLK": {"price": 220.0, "change_pct": 0.8, "direction": "▲"},
        "XLE": {"price": 88.0, "change_pct": -0.5, "direction": "▼"},
    },
    "top_sectors": [("XLK", {"change_pct": 0.8})],
    "bottom_sectors": [("XLE", {"change_pct": -0.5})],
}

MOCK_WATCHLIST = {
    "NVDA": {
        "symbol": "NVDA",
        "price": 875.0,
        "prev_close": 860.0,
        "premarket_change_pct": 1.74,
        "ema_8": 870.0,
        "ema_21": 855.0,
        "ema_50": 830.0,
        "ema_200": 780.0,
        "avg_volume_20d": 40_000_000,
        "today_volume": 35_000_000,
        "week52_high": 950.0,
    }
}

MOCK_SIGNALS = {
    "NVDA": {
        "bias": "bullish",
        "bias_score": 3,
        "flags": ["gap-up", "ema-stack-bullish", "above-200ema"],
        "note": "Gap-up +1.7% | EMA stack bullish | Above 200 EMA",
        "change_pct": 1.74,
    }
}

MOCK_NEWS = [
    {
        "title": "NVDA beats earnings",
        "source": "Bloomberg",
        "tickers": ["NVDA"],
        "published_at": "2025-05-06T07:00:00Z",
        "url": "https://example.com",
    }
]

MOCK_SENTIMENT = {"label": "Bullish", "score": 0.25, "by_ticker": {}}


def test_assemble_brief_has_required_keys():
    brief = assemble_brief(
        date="Tuesday, May 6, 2025",
        futures=MOCK_FUTURES,
        watchlist=MOCK_WATCHLIST,
        signals=MOCK_SIGNALS,
        news=MOCK_NEWS,
        sentiment=MOCK_SENTIMENT,
    )
    assert "date" in brief
    assert "futures" in brief
    assert "watchlist" in brief
    assert "news" in brief
    assert "sentiment" in brief
    assert "thesis" in brief
    assert brief["thesis"] is None  # not yet filled in


def test_watchlist_sorted_by_move():
    watchlist = {
        "A": {**MOCK_WATCHLIST["NVDA"], "symbol": "A", "premarket_change_pct": 0.5},
        "B": {**MOCK_WATCHLIST["NVDA"], "symbol": "B", "premarket_change_pct": 3.0},
    }
    signals = {
        "A": {**MOCK_SIGNALS["NVDA"], "change_pct": 0.5},
        "B": {**MOCK_SIGNALS["NVDA"], "change_pct": 3.0},
    }
    result = _format_watchlist(watchlist, signals)
    assert result[0]["symbol"] == "B"


def test_watchlist_emoji_bullish():
    result = _format_watchlist(MOCK_WATCHLIST, MOCK_SIGNALS)
    nvda = next(r for r in result if r["symbol"] == "NVDA")
    assert nvda["emoji"] == "🟢"


def test_news_capped_at_15():
    news = MOCK_NEWS * 20
    brief = assemble_brief("date", MOCK_FUTURES, MOCK_WATCHLIST, MOCK_SIGNALS, news, MOCK_SENTIMENT)
    assert len(brief["news"]) <= 15
