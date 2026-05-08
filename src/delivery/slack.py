"""
delivery/slack.py

Sends a compact pre-market brief to a Slack channel via incoming webhook.
"""

import json
import logging
from typing import Any

import requests

log = logging.getLogger(__name__)


def send_slack(brief: dict[str, Any], webhook_url: str) -> bool:
    """
    Post a compact brief to Slack via incoming webhook.
    Returns True on success.
    """
    blocks = _build_blocks(brief)

    try:
        resp = requests.post(
            webhook_url,
            data=json.dumps({"blocks": blocks}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Slack notification sent")
        return True
    except Exception as e:
        log.error(f"Slack send failed: {e}")
        return False


def _build_blocks(brief: dict) -> list[dict]:
    """Build Slack Block Kit blocks from the brief."""
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📈 Pre-Market Brief — {brief.get('date', '')}",
        },
    })

    # Macro
    futures_lines = []
    for label, value in list(brief.get("futures", {}).items())[:4]:
        futures_lines.append(f"*{label}*: {value}")

    sentiment = brief.get("sentiment", {})
    futures_lines.append(f"\n*Sentiment*: {sentiment.get('label', 'N/A')}")

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*MACRO PULSE*\n" + "\n".join(futures_lines),
        },
    })

    blocks.append({"type": "divider"})

    # Watchlist
    watchlist_lines = ["*WATCHLIST RADAR*"]
    for item in brief.get("watchlist", [])[:6]:
        pct = item["change_pct"]
        sign = "+" if pct >= 0 else ""
        watchlist_lines.append(
            f"{item['emoji']} *{item['symbol']}* {sign}{pct:.1f}%  |  {item['note']}"
        )

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(watchlist_lines)},
    })

    blocks.append({"type": "divider"})

    # Thesis
    thesis = brief.get("thesis", "")
    if thesis:
        # Slack has a 3000 char limit per block
        thesis_truncated = thesis[:2800] + "..." if len(thesis) > 2800 else thesis
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI TRADE THESIS*\n{thesis_truncated}",
            },
        })

    return blocks
