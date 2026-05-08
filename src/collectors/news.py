"""
collectors/news.py

Fetches financial news headlines for the watchlist.
Primary source: NewsAPI. Fallback: Yahoo Finance RSS.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import requests

log = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
YAHOO_RSS_BASE = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

# General market news feeds
MARKET_RSS_FEEDS = [
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
]


def fetch_news(tickers: list[str], max_per_ticker: int = 3) -> list[dict[str, Any]]:
    """
    Fetch recent news headlines for a list of tickers.
    Returns a flat list of news items sorted by recency.
    """
    all_news = []

    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        all_news.extend(_fetch_newsapi(tickers, api_key, max_per_ticker))
    else:
        log.info("No NEWS_API_KEY set — falling back to Yahoo Finance RSS")

    # Always pull Yahoo RSS as supplemental source
    all_news.extend(_fetch_yahoo_rss(tickers, max_per_ticker))

    # Deduplicate by title
    seen = set()
    unique_news = []
    for item in all_news:
        key = item["title"][:60]
        if key not in seen:
            seen.add(key)
            unique_news.append(item)

    # Sort by published date descending
    unique_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    log.info(f"Collected {len(unique_news)} unique news items")
    return unique_news[:30]  # cap at 30 for token budget


def _fetch_newsapi(tickers: list[str], api_key: str, max_per_ticker: int) -> list[dict]:
    """Fetch from NewsAPI.org."""
    results = []
    query = " OR ".join(tickers[:5])  # NewsAPI query limit
    from_date = (datetime.now(timezone.utc) - timedelta(hours=18)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": api_key,
        "pageSize": max_per_ticker * len(tickers),
    }

    try:
        resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for article in data.get("articles", []):
            results.append({
                "title": article.get("title", ""),
                "source": article.get("source", {}).get("name", "NewsAPI"),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "summary": article.get("description", ""),
                "tickers": _tag_tickers(article.get("title", "") + " " + article.get("description", ""), tickers),
            })

    except Exception as e:
        log.warning(f"NewsAPI fetch failed: {e}")

    return results


def _fetch_yahoo_rss(tickers: list[str], max_per_ticker: int) -> list[dict]:
    """Fetch from Yahoo Finance RSS per ticker."""
    results = []

    for ticker in tickers[:8]:  # cap to avoid rate limits
        url = YAHOO_RSS_BASE.format(ticker=ticker)
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_ticker]:
                results.append({
                    "title": entry.get("title", ""),
                    "source": "Yahoo Finance",
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "tickers": [ticker],
                })
        except Exception as e:
            log.warning(f"Yahoo RSS failed for {ticker}: {e}")

    return results


def _tag_tickers(text: str, tickers: list[str]) -> list[str]:
    """Find which tickers are mentioned in a text blob."""
    text_upper = text.upper()
    return [t for t in tickers if t.upper() in text_upper]
