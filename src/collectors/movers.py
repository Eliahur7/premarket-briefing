"""
collectors/movers.py

Fetches top 10 S&P 500 pre-market gainers and losers.
Uses yfinance to get real-time pre-market movement data.
"""

import logging
from typing import Any

import yfinance as yf

log = logging.getLogger(__name__)

# Top S&P 500 components (sample of most liquid/tracked)
SP500_TICKERS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "BRK.B", "JNJ", "V",
    "WMT", "PG", "COST", "MCD", "DIS", "NFLX", "ADBE", "CRM", "AMD", "INTC",
    "QCOM", "CSCO", "PEP", "KO", "MU", "AVGO", "TXN", "INTU", "SNPS", "AMAT",
    "ASML", "LRCX", "UNH", "LLY", "AZO", "BKNG", "PYPL", "SQ", "SHOP", "UBER",
    "PLTR", "COIN", "RIOT", "MSTR", "ARKK", "SOFI", "HOOD", "MARA", "CLSK", "MINER"
]


def fetch_movers() -> dict[str, Any]:
    """
    Fetch top 10 pre-market gainers and losers from S&P 500.
    Returns dict with 'gainers' and 'losers' lists.
    """
    movers = {"gainers": [], "losers": [], "errors": []}

    # Fetch data for all tickers
    ticker_data = {}
    for symbol in SP500_TICKERS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)

            if price and prev_close and prev_close != 0:
                change_pct = ((price - prev_close) / prev_close) * 100
                ticker_data[symbol] = {
                    "price": round(price, 2),
                    "prev_close": round(prev_close, 2),
                    "change_pct": round(change_pct, 2),
                    "change_amount": round(price - prev_close, 2),
                }
        except Exception as e:
            movers["errors"].append({"symbol": symbol, "error": str(e)})

    # Sort by change_pct to find gainers and losers
    if ticker_data:
        sorted_tickers = sorted(
            ticker_data.items(),
            key=lambda x: x[1]["change_pct"],
            reverse=True
        )

        # Top 10 gainers
        movers["gainers"] = [
            {
                "symbol": symbol,
                "price": data["price"],
                "prev_close": data["prev_close"],
                "change_pct": data["change_pct"],
                "change_amount": data["change_amount"],
            }
            for symbol, data in sorted_tickers[:10]
        ]

        # Top 10 losers (bottom 10 sorted ascending, then reversed for display)
        movers["losers"] = [
            {
                "symbol": symbol,
                "price": data["price"],
                "prev_close": data["prev_close"],
                "change_pct": data["change_pct"],
                "change_amount": data["change_amount"],
            }
            for symbol, data in sorted_tickers[-10:][::-1]
        ]

        log.info(f"Fetched top 10 gainers and losers ({len(ticker_data)} tickers analyzed)")
    else:
        log.warning("No ticker data collected for movers")

    return movers
