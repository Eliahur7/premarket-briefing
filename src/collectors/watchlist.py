"""
collectors/watchlist.py

Fetches pre-market data for a list of tickers.
Pulls price, pre-market change, volume, 50/200 EMA, and key info.
"""

import logging
from typing import Any

import yfinance as yf
import pandas as pd

log = logging.getLogger(__name__)


def fetch_watchlist(tickers: list[str]) -> dict[str, Any]:
    """
    For each ticker, fetch pre-market quote and recent OHLCV history.
    Returns a dict keyed by ticker symbol.
    """
    results = {}

    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            # Current / pre-market price
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)
            market_cap = getattr(info, "market_cap", None)

            # Historical daily data (90 days for EMA calculation)
            hist = ticker.history(period="90d", interval="1d")

            ema_8 = ema_21 = ema_50 = ema_200 = None
            avg_volume = None
            today_volume = None

            if not hist.empty:
                closes = hist["Close"]
                ema_8 = float(closes.ewm(span=8).mean().iloc[-1])
                ema_21 = float(closes.ewm(span=21).mean().iloc[-1])
                ema_50 = float(closes.ewm(span=50).mean().iloc[-1])
                ema_200 = float(closes.ewm(span=200).mean().iloc[-1])
                avg_volume = float(hist["Volume"].rolling(20).mean().iloc[-1])
                today_volume = float(hist["Volume"].iloc[-1]) if len(hist) > 0 else None

            # Pre-market change
            change_pct = None
            if price and prev_close and prev_close != 0:
                change_pct = round(((price - prev_close) / prev_close) * 100, 2)

            # 52-week high/low
            week52_high = getattr(info, "year_high", None)
            week52_low = getattr(info, "year_low", None)

            results[symbol] = {
                "symbol": symbol,
                "price": round(price, 2) if price else None,
                "prev_close": round(prev_close, 2) if prev_close else None,
                "premarket_change_pct": change_pct,
                "market_cap": market_cap,
                "ema_8": round(ema_8, 2) if ema_8 else None,
                "ema_21": round(ema_21, 2) if ema_21 else None,
                "ema_50": round(ema_50, 2) if ema_50 else None,
                "ema_200": round(ema_200, 2) if ema_200 else None,
                "avg_volume_20d": int(avg_volume) if avg_volume else None,
                "today_volume": int(today_volume) if today_volume else None,
                "week52_high": round(week52_high, 2) if week52_high else None,
                "week52_low": round(week52_low, 2) if week52_low else None,
            }

            log.info(f"  {symbol}: {change_pct:+.2f}%" if change_pct else f"  {symbol}: no change data")

        except Exception as e:
            log.warning(f"Failed to fetch watchlist data for {symbol}: {e}")
            results[symbol] = {"symbol": symbol, "error": str(e)}

    return results
