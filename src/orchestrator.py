"""
orchestrator.py — Lambda handler and local entrypoint.

Runs the full pre-market briefing pipeline:
  collect → analyze → format → AI thesis → deliver
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from src.collectors.futures import fetch_futures
from src.collectors.news import fetch_news
from src.collectors.watchlist import fetch_watchlist
from src.analyzers.sentiment import analyze_sentiment
from src.analyzers.signals import analyze_signals
from src.ai.thesis import generate_thesis
from src.formatters.brief import assemble_brief
from src.delivery.email import send_email
from src.delivery.slack import send_slack

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


def run(dry_run: bool = False) -> dict:
    """
    Execute the full briefing pipeline.
    Returns the assembled brief dict.
    """
    log.info("=== Pre-Market Briefing Pipeline Starting ===")
    today = datetime.now().strftime("%A, %B %-d, %Y")

    watchlist = [t.strip() for t in os.getenv("WATCHLIST", "NVDA,AMD,GOOGL").split(",")]
    sector_etfs = [t.strip() for t in os.getenv("SECTOR_ETFS", "XLK,XLF,XLE").split(",")]

    # ── 1. Collect ────────────────────────────────────────────────────────────
    log.info("Step 1/5: Collecting market data...")
    futures_data = fetch_futures()
    watchlist_data = fetch_watchlist(watchlist)
    news_items = fetch_news(watchlist)

    # ── 2. Analyze ────────────────────────────────────────────────────────────
    log.info("Step 2/5: Analyzing signals...")
    signals = analyze_signals(watchlist_data)
    sentiment = analyze_sentiment(news_items)

    # ── 3. Format ─────────────────────────────────────────────────────────────
    log.info("Step 3/5: Assembling brief...")
    brief = assemble_brief(
        date=today,
        futures=futures_data,
        watchlist=watchlist_data,
        signals=signals,
        news=news_items,
        sentiment=sentiment,
    )

    # ── 4. AI Thesis ──────────────────────────────────────────────────────────
    log.info("Step 4/5: Generating AI trade thesis...")
    thesis = generate_thesis(brief)
    brief["thesis"] = thesis

    # ── 5. Deliver ────────────────────────────────────────────────────────────
    if dry_run:
        log.info("Step 5/5: DRY RUN — printing brief to stdout")
        _print_brief(brief)
    else:
        log.info("Step 5/5: Delivering briefing...")
        send_email(brief)

        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_url:
            send_slack(brief, slack_url)

    log.info("=== Pipeline Complete ===")
    return brief


def _print_brief(brief: dict) -> None:
    """Pretty-print the brief to stdout for local testing."""
    print("\n" + "=" * 60)
    print(f"📊 PRE-MARKET BRIEF — {brief['date']} | 7:30 AM CT")
    print("=" * 60)

    print("\nMACRO PULSE")
    for k, v in brief.get("futures", {}).items():
        print(f"  {k}: {v}")

    print("\nWATCHLIST RADAR")
    for ticker, data in brief.get("watchlist", {}).items():
        sig = brief.get("signals", {}).get(ticker, {})
        emoji = "🟢" if sig.get("bias") == "bullish" else ("🔴" if sig.get("bias") == "bearish" else "🟡")
        pct = data.get("premarket_change_pct", 0)
        note = sig.get("note", "")
        print(f"  {emoji} {ticker:<6} {pct:+.1f}%  |  {note}")

    print("\nMARKET SENTIMENT")
    print(f"  Overall: {brief.get('sentiment', {}).get('label', 'Neutral')}")

    print("\nAI TRADE THESIS")
    thesis = brief.get("thesis", "Not generated.")
    for line in thesis.split("\n"):
        print(f"  {line}")

    print("\n" + "=" * 60 + "\n")


# ── Lambda Handler ─────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entrypoint."""
    try:
        brief = run(dry_run=False)
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "ok", "date": brief.get("date")}),
        }
    except Exception as e:
        log.exception("Pipeline failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": str(e)}),
        }


# ── CLI Entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-Market Briefing Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("DRY_RUN", "false").lower() == "true",
        help="Print brief to stdout instead of sending email",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
