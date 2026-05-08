"""tests/test_sentiment.py"""
import pytest
from unittest.mock import patch, MagicMock
from src.analyzers.sentiment import analyze_sentiment, _label


def _mock_vader_scores(text):
    """Simple keyword-based mock for VADER scores."""
    positive_words = ["surge", "soars", "crushes", "exceptional", "growth", "beat", "boom", "higher", "strong"]
    negative_words = ["crash", "fears", "worries", "misses", "collapses", "struggles", "weak"]
    text_lower = text.lower()
    pos = sum(1 for w in positive_words if w in text_lower)
    neg = sum(1 for w in negative_words if w in text_lower)
    score = (pos - neg) * 0.15
    return {"compound": max(-1.0, min(1.0, score))}


def _patch_vader(monkeypatch):
    mock_vader = MagicMock()
    mock_vader.polarity_scores.side_effect = _mock_vader_scores
    import src.analyzers.sentiment as sent_mod
    monkeypatch.setattr(sent_mod, "_vader", mock_vader)


def test_label_bullish():
    assert _label(0.3) == "Bullish"


def test_label_bearish():
    assert _label(-0.3) == "Bearish"


def test_label_neutral():
    assert _label(0.01) == "Neutral"


def test_label_mildly_bullish():
    assert _label(0.08) == "Mildly Bullish"


def test_empty_news(monkeypatch):
    _patch_vader(monkeypatch)
    result = analyze_sentiment([])
    assert result["score"] == 0.0
    assert result["label"] == "Neutral"
    assert result["by_ticker"] == {}


def test_positive_headlines(monkeypatch):
    _patch_vader(monkeypatch)
    news = [
        {"title": "NVDA crushes earnings with record revenue and profit surge", "summary": "", "tickers": ["NVDA"]},
        {"title": "Markets surge higher on strong economic data", "summary": "", "tickers": []},
        {"title": "AMD reports exceptional growth and raises guidance", "summary": "", "tickers": ["AMD"]},
    ]
    result = analyze_sentiment(news)
    assert result["score"] > 0
    assert result["label"] in ("Bullish", "Mildly Bullish")


def test_negative_headlines(monkeypatch):
    _patch_vader(monkeypatch)
    news = [
        {"title": "Markets crash on recession fears and rate hike worries", "summary": "", "tickers": []},
        {"title": "GOOGL misses earnings badly as revenue collapses", "summary": "", "tickers": ["GOOGL"]},
    ]
    result = analyze_sentiment(news)
    assert result["score"] < 0


def test_per_ticker_sentiment(monkeypatch):
    _patch_vader(monkeypatch)
    news = [
        {"title": "NVDA soars to all-time high on AI boom", "summary": "", "tickers": ["NVDA"]},
        {"title": "AMD struggles amid weak demand and inventory issues", "summary": "", "tickers": ["AMD"]},
    ]
    result = analyze_sentiment(news)
    assert "NVDA" in result["by_ticker"]
    assert "AMD" in result["by_ticker"]
    assert result["by_ticker"]["NVDA"]["score"] > result["by_ticker"]["AMD"]["score"]
