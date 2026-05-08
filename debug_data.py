#!/usr/bin/env python3
"""Debug script to output all raw pipeline data as JSON."""

import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.collectors.futures import fetch_futures
from src.collectors.movers import fetch_movers
from src.collectors.watchlist import fetch_watchlist
from src.collectors.news import fetch_news
from src.analyzers.sentiment import analyze_sentiment
from src.analyzers.signals import analyze_signals
from src.formatters.brief import assemble_brief

logging.basicConfig(level=logging.ERROR)

print("=" * 60)
print("PRE-MARKET BRIEFING — RAW DATA DEBUG")
print("=" * 60)

# Get watchlist from env
watchlist = [t.strip() for t in os.getenv("WATCHLIST", "NVDA,AMD,GOOGL").split(",")]

# Collect all data
futures = fetch_futures()
movers = fetch_movers()
watchlist_data = fetch_watchlist(watchlist)
news = fetch_news(watchlist)
sentiment = analyze_sentiment(news)
signals = analyze_signals(watchlist_data)

# Assemble brief
date = datetime.now().strftime("%A, %B %-d, %Y")
brief = assemble_brief(date, futures, movers, watchlist_data, signals, news, sentiment)

# Output JSON
print(json.dumps(brief, indent=2, default=str))
