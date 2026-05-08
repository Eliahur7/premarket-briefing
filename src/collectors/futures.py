"""
collectors/futures.py

Fetches macro futures and index pre-market data.
Uses yfinance for S&P 500 futures, Nasdaq futures, VIX, and sector ETFs.
"""

import logging
from typing import Any

import yfinance as yf

log = logging.getLogger(__name__)

# Futures proxies available via yfinance
FUTURES_TICKERS = {
    "ES=F": "S&P 500 Futures",
    "NQ=F": "Nasdaq Futures",
    "YM=F": "Dow Futures",
    "RTY=F": "Russell 2000 Futures",
    "^VIX": "VIX",
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "DX-Y.NYB": "USD Index",
}

SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLU", "XLY", "XLI", "XLB", "XLRE", "XLC", "XLP"]


def fetch_futures() -> dict[str, Any]:
    """
    Fetch pre-market futures and sector ETF data.
    Returns a structured dict with macro context.
    """
    result = {"futures": {}, "sectors": {}, "errors": []}

    # ── Futures ───────────────────────────────────────────────────────────────
    for symbol, label in FUTURES_TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)

            if price and prev_close and prev_close != 0:
                change_pct = ((price - prev_close) / prev_close) * 100
                result["futures"][label] = {
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "direction": "▲" if change_pct >= 0 else "▼",
                }
            else:
                result["futures"][label] = {"symbol": symbol, "price": None, "change_pct": None}

        except Exception as e:
            log.warning(f"Failed to fetch {symbol}: {e}")
            result["errors"].append(symbol)

    # ── Sector ETFs ───────────────────────────────────────────────────────────
    for symbol in SECTOR_ETFS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)

            if price and prev_close and prev_close != 0:
                change_pct = ((price - prev_close) / prev_close) * 100
                result["sectors"][symbol] = {
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "direction": "▲" if change_pct >= 0 else "▼",
                }
        except Exception as e:
            log.warning(f"Failed to fetch sector ETF {symbol}: {e}")

    # Derive top/bottom sectors
    sorted_sectors = sorted(
        [(k, v) for k, v in result["sectors"].items() if v.get("change_pct") is not None],
        key=lambda x: x[1]["change_pct"],
        reverse=True,
    )
    result["top_sectors"] = sorted_sectors[:3]
    result["bottom_sectors"] = sorted_sectors[-3:]

    log.info(f"Fetched {len(result['futures'])} futures, {len(result['sectors'])} sectors")
    return result
