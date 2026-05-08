"""
analyzers/sentiment.py

Runs lightweight sentiment analysis on news headlines.
Uses NLTK VADER — no API calls required, runs offline.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)

# Lazy-load VADER to avoid cold-start penalty if not needed
_vader = None


def _get_vader():
    global _vader
    if _vader is None:
        try:
            import nltk
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            nltk.download("vader_lexicon", quiet=True)
            _vader = SentimentIntensityAnalyzer()
        except ImportError:
            log.warning("NLTK not available — sentiment analysis disabled")
    return _vader


def analyze_sentiment(news_items: list[dict]) -> dict[str, Any]:
    """
    Score each news headline and aggregate into an overall market sentiment.
    Returns a dict with per-ticker sentiment and overall label.
    """
    vader = _get_vader()

    if not vader:
        return {"label": "Unavailable", "score": 0.0, "by_ticker": {}}

    ticker_scores: dict[str, list[float]] = {}
    all_scores = []

    for item in news_items:
        text = item.get("title", "") + " " + item.get("summary", "")
        scores = vader.polarity_scores(text)
        compound = scores["compound"]
        all_scores.append(compound)

        for ticker in item.get("tickers", []):
            ticker_scores.setdefault(ticker, []).append(compound)

    # Aggregate
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

    by_ticker = {}
    for ticker, scores in ticker_scores.items():
        avg = sum(scores) / len(scores)
        by_ticker[ticker] = {
            "score": round(avg, 3),
            "label": _label(avg),
            "headline_count": len(scores),
        }

    return {
        "score": round(overall_score, 3),
        "label": _label(overall_score),
        "by_ticker": by_ticker,
        "total_headlines": len(all_scores),
    }


def _label(score: float) -> str:
    if score >= 0.15:
        return "Bullish"
    elif score >= 0.05:
        return "Mildly Bullish"
    elif score <= -0.15:
        return "Bearish"
    elif score <= -0.05:
        return "Mildly Bearish"
    else:
        return "Neutral"
