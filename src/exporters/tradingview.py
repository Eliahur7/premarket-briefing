"""
src/exporters/tradingview.py

Generates PineScript v5 indicator code for TradingView, allowing traders
to copy-paste key pre-market levels (Pre-Market High, Pre-Market Low, Previous Close,
Gap Zones, and Moving Averages) directly into TradingView.
"""

import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


def generate_pinescript(ticker: str, data: Dict[str, Any]) -> str:
    """
    Generates valid PineScript v5 code for TradingView tailored to the specific ticker and levels.
    """
    price = data.get("price", 0.0)
    prev_close = data.get("prev_close", 0.0)
    pmh = data.get("premarket_high", price * 1.01 if price else 100.0)
    pml = data.get("premarket_low", price * 0.99 if price else 98.0)
    ema_8 = data.get("ema_8", 0.0)
    ema_21 = data.get("ema_21", 0.0)
    ema_50 = data.get("ema_50", 0.0)
    
    # Format floating numbers cleanly
    pinescript_code = f"""//@version=5
indicator("Premarket Pulse Key Levels — {ticker}", overlay=true)

// ==============================================================================
// PRE-MARKET & MACRO LEVELS
// ==============================================================================
var float pm_high = {pmh:.2f}
var float pm_low  = {pml:.2f}
var float pd_close = {prev_close:.2f}

// Plot Lines
plot(pm_high, "Pre-Market High (PMH)", color=color.new(color.green, 0), linewidth=2, style=plot.style_linebr)
plot(pm_low, "Pre-Market Low (PML)", color=color.new(color.red, 0), linewidth=2, style=plot.style_linebr)
plot(pd_close, "Previous Close (PDC)", color=color.new(color.gray, 20), linewidth=1, style=plot.style_dashed)

// Fill Gap Zone
p1 = plot(pm_high, display=display.none)
p2 = plot(pd_close, display=display.none)
fill(p1, p2, color=pm_high > pd_close ? color.new(color.green, 90) : color.new(color.red, 90), title="Pre-Market Gap Zone")

// ==============================================================================
// KEY MOVING AVERAGES
// ==============================================================================
ema8  = ta.ema(close, 8)
ema21 = ta.ema(close, 21)
sma50 = ta.sma(close, 50)

plot(ema8, "8 EMA", color=color.new(#38bdf8, 0), linewidth=1)
plot(ema21, "21 EMA", color=color.new(#fbbf24, 0), linewidth=1)
plot(sma50, "50 SMA", color=color.new(#a855f7, 0), linewidth=2)

// ==============================================================================
// TABLE SUMMARY
// ==============================================================================
var table info_table = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 30), border_color=color.gray, border_width=1)
if barstate.islast
    table.cell(info_table, 0, 0, "Ticker", text_color=color.white, text_size=size.small)
    table.cell(info_table, 1, 0, "{ticker}", text_color=color.yellow, text_size=size.small)
    table.cell(info_table, 0, 1, "PM High", text_color=color.green, text_size=size.small)
    table.cell(info_table, 1, 1, str.tostring(pm_high), text_color=color.white, text_size=size.small)
    table.cell(info_table, 0, 2, "PM Low", text_color=color.red, text_size=size.small)
    table.cell(info_table, 1, 2, str.tostring(pm_low), text_color=color.white, text_size=size.small)
    table.cell(info_table, 0, 3, "Prev Close", text_color=color.gray, text_size=size.small)
    table.cell(info_table, 1, 3, str.tostring(pd_close), text_color=color.white, text_size=size.small)
"""
    return pinescript_code.strip()


def export_levels_summary(watchlist_data: Dict[str, Any]) -> str:
    """
    Returns a clean Markdown table of key pre-market levels for quick reference.
    """
    lines = [
        "| Ticker | Price | Gap % | Pre-Market High | Pre-Market Low | Prev Close | 50 EMA |",
        "|---|---|---|---|---|---|---|"
    ]
    for symbol, d in watchlist_data.items():
        if "error" in d:
            continue
        price = f"${d.get('price', 0):,.2f}"
        gap = f"{d.get('premarket_change_pct', 0):+,.2f}%"
        pmh = f"${d.get('premarket_high', 0):,.2f}" if d.get('premarket_high') else "N/A"
        pml = f"${d.get('premarket_low', 0):,.2f}" if d.get('premarket_low') else "N/A"
        pdc = f"${d.get('prev_close', 0):,.2f}" if d.get('prev_close') else "N/A"
        ema50 = f"${d.get('ema_50', 0):,.2f}" if d.get('ema_50') else "N/A"
        lines.append(f"| **{symbol}** | {price} | {gap} | {pmh} | {pml} | {pdc} | {ema50} |")
    
    return "\n".join(lines)
