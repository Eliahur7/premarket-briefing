"""
formatters/brief.py

Assembles raw collected + analyzed data into a clean brief dict
that can be passed to the AI thesis generator and email template.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)


def assemble_brief(
    date: str,
    futures: dict,
    movers: dict,
    watchlist: dict,
    signals: dict,
    news: list,
    sentiment: dict,
) -> dict[str, Any]:
    """
    Combine all pipeline outputs into a single structured brief.
    This dict is the single source of truth passed to both
    the AI thesis and the email template.
    """
    brief = {
        "date": date,
        "futures": _format_futures(futures),
        "sectors": _format_sectors(futures),
        "movers": _format_movers(movers),
        "watchlist": _format_watchlist(watchlist, signals),
        "news": _format_news(news),
        "sentiment": sentiment,
        "thesis": None,  # filled in by orchestrator after AI call
    }

    log.info(f"Brief assembled: {len(brief['watchlist'])} tickers, {len(brief['movers']['gainers'])} gainers, {len(brief['news'])} headlines")
    return brief


def _format_futures(futures: dict) -> dict:
    """Format futures into a clean summary dict."""
    formatted = {}
    for label, data in futures.get("futures", {}).items():
        if data.get("change_pct") is not None:
            pct = data["change_pct"]
            direction = "▲" if pct >= 0 else "▼"
            formatted[label] = f"{direction} {abs(pct):.2f}%  (${data['price']:,.2f})"
    return formatted


def _format_sectors(futures: dict) -> dict:
    """Format sector ETF data into leaders/laggards."""
    top = futures.get("top_sectors", [])
    bottom = futures.get("bottom_sectors", [])

    return {
        "leaders": [
            {"symbol": s, "change_pct": d.get("change_pct", 0)}
            for s, d in top
        ],
        "laggards": [
            {"symbol": s, "change_pct": d.get("change_pct", 0)}
            for s, d in bottom
        ],
    }


def _format_movers(movers: dict) -> dict:
    """Format top 10 gainers and losers."""
    return {
        "gainers": movers.get("gainers", []),
        "losers": movers.get("losers", []),
    }


def _format_watchlist(watchlist: dict, signals: dict) -> list[dict]:
    """Merge watchlist quotes with signals into a sortable list."""
    items = []
    for symbol, data in watchlist.items():
        sig = signals.get(symbol, {})
        change_pct = data.get("premarket_change_pct", 0) or 0

        emoji = "🟢" if "bullish" in sig.get("bias", "") else (
            "🔴" if "bearish" in sig.get("bias", "") else "🟡"
        )

        items.append({
            "symbol": symbol,
            "emoji": emoji,
            "price": data.get("price"),
            "prev_close": data.get("prev_close"),
            "change_pct": change_pct,
            "bias": sig.get("bias", "neutral"),
            "bias_score": sig.get("bias_score", 0),
            "note": sig.get("note", ""),
            "flags": sig.get("flags", []),
            "ema_50": data.get("ema_50"),
            "ema_200": data.get("ema_200"),
            "week52_high": data.get("week52_high"),
        })

    # Sort: biggest movers first, then by bias score
    items.sort(key=lambda x: (abs(x["change_pct"]), x["bias_score"]), reverse=True)
    return items


def _format_news(news: list) -> list[dict]:
    """Keep only the fields needed for display / AI context."""
    return [
        {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "tickers": item.get("tickers", []),
            "published_at": item.get("published_at", ""),
            "url": item.get("url", ""),
        }
        for item in news[:15]
    ]
