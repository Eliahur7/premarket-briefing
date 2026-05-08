"""
ai/thesis.py

Calls the Anthropic Claude API to generate a synthesized trade thesis
from the assembled brief data.
"""

import logging
import os
from typing import Any

import anthropic

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a sharp, experienced equity trader providing a concise pre-market brief 
to a sophisticated investor. You think in terms of setups, catalysts, risk/reward, and 
key levels. You are direct — no hedging, no disclaimers, no "please consult a financial advisor."

Your output is a 3–5 paragraph trade thesis covering:
1. The macro tape and what it signals for the open
2. Your top 1–2 actionable setups from the watchlist (specific entry logic, stop placement, target)
3. What to avoid or watch out for today

Write like a trader, not a newsletter. Be specific about price levels when you have them.
Keep the full response under 350 words."""


def generate_thesis(brief: dict[str, Any]) -> str:
    """
    Generate an AI trade thesis from the assembled brief.
    Returns a plain-text thesis string.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — skipping AI thesis")
        return "AI thesis unavailable — set ANTHROPIC_API_KEY to enable."

    prompt = _build_prompt(brief)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        thesis = message.content[0].text.strip()
        log.info(f"AI thesis generated ({len(thesis)} chars)")
        return thesis

    except Exception as e:
        log.error(f"Anthropic API call failed: {e}")
        return f"AI thesis generation failed: {e}"


def _build_prompt(brief: dict) -> str:
    """Convert the brief dict into a structured prompt for Claude."""
    lines = [f"DATE: {brief['date']}", ""]

    # Macro
    lines.append("MACRO FUTURES:")
    for label, value in brief.get("futures", {}).items():
        lines.append(f"  {label}: {value}")

    # Sectors
    sectors = brief.get("sectors", {})
    leaders = sectors.get("leaders", [])
    laggards = sectors.get("laggards", [])
    if leaders:
        lines.append(f"\nTOP SECTORS: {', '.join(f\"{s['symbol']} {s['change_pct']:+.1f}%\" for s in leaders)}")
    if laggards:
        lines.append(f"WEAK SECTORS: {', '.join(f\"{s['symbol']} {s['change_pct']:+.1f}%\" for s in laggards)}")

    # Sentiment
    sentiment = brief.get("sentiment", {})
    lines.append(f"\nNEWS SENTIMENT: {sentiment.get('label', 'Neutral')} (score: {sentiment.get('score', 0):.2f})")

    # Watchlist
    lines.append("\nWATCHLIST:")
    for item in brief.get("watchlist", []):
        price_str = f"${item['price']:.2f}" if item.get("price") else "N/A"
        lines.append(
            f"  {item['symbol']}: {item['change_pct']:+.1f}% pre-mkt | {price_str} | "
            f"Bias: {item['bias']} | {item['note']}"
        )
        if item.get("flags"):
            lines.append(f"    Flags: {', '.join(item['flags'])}")

    # News
    lines.append("\nTOP HEADLINES:")
    for headline in brief.get("news", [])[:10]:
        tickers = ", ".join(headline.get("tickers", [])) or "market"
        lines.append(f"  [{tickers}] {headline['title']}")

    lines.append("\nGenerate the pre-market trade thesis:")
    return "\n".join(lines)
