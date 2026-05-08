"""
delivery/email.py

Sends the pre-market brief as an HTML email via AWS SES.
"""

import logging
import os
from typing import Any

import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape

log = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "formatters")


def send_email(brief: dict[str, Any]) -> bool:
    """
    Render the HTML email template and send via AWS SES.
    Returns True on success.
    """
    from_email = os.getenv("SES_FROM_EMAIL")
    to_email = os.getenv("SES_TO_EMAIL")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not from_email or not to_email:
        log.error("SES_FROM_EMAIL or SES_TO_EMAIL not configured")
        return False

    html_body = _render_template(brief)
    text_body = _render_plaintext(brief)
    subject = f"📈 Pre-Market Brief — {brief['date']}"

    try:
        ses = boto3.client("ses", region_name=region)
        response = ses.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        message_id = response["MessageId"]
        log.info(f"Email sent via SES: {message_id}")
        return True

    except Exception as e:
        log.error(f"SES send failed: {e}")
        return False


def _render_template(brief: dict) -> str:
    """Render the Jinja2 HTML email template."""
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("email_template.html")
        return template.render(**brief)
    except Exception as e:
        log.warning(f"Template render failed, using plaintext fallback: {e}")
        return f"<pre>{_render_plaintext(brief)}</pre>"


def _render_plaintext(brief: dict) -> str:
    """Generate a plain-text version of the brief."""
    lines = [
        f"PRE-MARKET BRIEF — {brief.get('date', '')}",
        "=" * 50,
        "",
        "MACRO PULSE",
    ]

    for label, value in brief.get("futures", {}).items():
        lines.append(f"  {label}: {value}")

    lines += ["", "WATCHLIST RADAR"]
    for item in brief.get("watchlist", []):
        lines.append(
            f"  {item['emoji']} {item['symbol']:<6} {item['change_pct']:+.1f}%  |  {item['note']}"
        )

    sentiment = brief.get("sentiment", {})
    lines += [
        "",
        f"MARKET SENTIMENT: {sentiment.get('label', 'Neutral')}",
        "",
        "AI TRADE THESIS",
        "-" * 40,
        brief.get("thesis", "Not available"),
        "",
        "=" * 50,
        "Pre-Market Briefing Bot",
    ]

    return "\n".join(lines)
