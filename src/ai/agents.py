"""
src/ai/agents.py

Multi-Agent Trading Desk System.
Implements specialized agents for Macro/Fed sentiment, Technical/Liquidity,
and Catalyst/News analysis, orchestrated by a Chief Trading Desk Portfolio Manager.
"""

import json
import logging
import os
from typing import Any, Dict, List

import anthropic

log = logging.getLogger(__name__)


class MacroAgent:
    """Agent responsible for classifying the global macro regime and market risk environment."""
    
    def analyze(self, futures: Dict[str, Any]) -> Dict[str, Any]:
        import re
        sp_pct = 0.0
        nq_pct = 0.0
        vix_val = 15.0
        
        sp_val = futures.get("S&P 500 Futures")
        if isinstance(sp_val, dict):
            sp_pct = sp_val.get("pct", 0.0)
        elif isinstance(sp_val, str):
            match = re.search(r'([+-]?\d+\.?\d*)%', sp_val)
            if match:
                sp_pct = float(match.group(1))
                if "▼" in sp_val and sp_pct > 0:
                    sp_pct = -sp_pct

        nq_val = futures.get("Nasdaq Futures")
        if isinstance(nq_val, dict):
            nq_pct = nq_val.get("pct", 0.0)
        elif isinstance(nq_val, str):
            match = re.search(r'([+-]?\d+\.?\d*)%', nq_val)
            if match:
                nq_pct = float(match.group(1))
                if "▼" in nq_val and nq_pct > 0:
                    nq_pct = -nq_pct

        vix_val_raw = futures.get("Volatility Index (VIX)")
        if isinstance(vix_val_raw, dict):
            vix_val = vix_val_raw.get("price", 15.0)
        elif isinstance(vix_val_raw, str):
            match = re.search(r'\$(\d+\.?\d*)', vix_val_raw)
            if match:
                vix_val = float(match.group(1))
        
        if vix_val > 22.0:
            regime = "High Volatility / Panic Risk"
            bias = "Cautious / Defensive"
        elif sp_pct > 0.5 and nq_pct > 0.5:
            regime = "Risk-On Momentum"
            bias = "Bullish Long Bias"
        elif sp_pct < -0.5 and nq_pct < -0.5:
            regime = "Risk-Off Liquidation"
            bias = "Bearish Short / Hedged Bias"
        else:
            regime = "Compression / Consolidation Chop"
            bias = "Neutral Range-Bound"
            
        return {
            "regime": regime,
            "bias": bias,
            "sp_change_pct": sp_pct,
            "nq_change_pct": nq_pct,
            "vix": vix_val
        }


class TechnicalAgent:
    """Agent responsible for analyzing gap conditions, EMA stacks, and breakout levels."""
    
    def analyze(self, watchlist: List[Dict[str, Any]], signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        setups = []
        for item in watchlist:
            symbol = item.get("symbol")
            signal = signals.get(symbol, {})
            pct = item.get("change_pct", 0.0)
            flags = signal.get("flags", [])
            
            setup_type = "Watch / Neutral"
            if "strong-gap-up" in flags or (pct > 1.5 and "ema-stack-bullish" in flags):
                setup_type = "Gap & Go (Long Breakout)"
            elif "strong-gap-down" in flags or (pct < -1.5 and "ema-stack-bearish" in flags):
                setup_type = "Gap & Fade / Breakdown"
            elif "above-50ema" in flags and pct > 0:
                setup_type = "Trend Continuation Long"
                
            setups.append({
                "symbol": symbol,
                "price": item.get("price", 0.0),
                "change_pct": pct,
                "setup_type": setup_type,
                "flags": flags,
                "bias": signal.get("bias", "neutral")
            })
        return setups


class CatalystAgent:
    """Agent responsible for evaluating news sentiment and earnings headlines."""
    
    def analyze(self, news: List[Dict[str, Any]], sentiment: Dict[str, Any]) -> Dict[str, Any]:
        high_impact_headlines = []
        for n in news[:5]:
            high_impact_headlines.append(f"[{', '.join(n.get('tickers', []))}] {n.get('title')}")
            
        return {
            "overall_sentiment": sentiment.get("label", "Neutral"),
            "sentiment_score": sentiment.get("score", 0.0),
            "top_catalysts": high_impact_headlines
        }


class ChiefTradingDesk:
    """
    Synthesizes outputs from Macro, Technical, and Catalyst agents
    into a structured multi-agent trade thesis and trade plan.
    """
    
    def __init__(self):
        self.macro_agent = MacroAgent()
        self.technical_agent = TechnicalAgent()
        self.catalyst_agent = CatalystAgent()
        
    def generate_trading_plan(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        macro = self.macro_agent.analyze(brief.get("futures", {}))
        tech = self.technical_agent.analyze(brief.get("watchlist", []), brief.get("signals", {}))
        catalyst = self.catalyst_agent.analyze(brief.get("news", []), brief.get("sentiment", {}))
        
        # Build prompt for Claude/LLM synthesis
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            log.warning("ANTHROPIC_API_KEY not set — using rule-based multi-agent fallback.")
            return self._build_rule_based_fallback(macro, tech, catalyst, brief)
            
        try:
            client = anthropic.Anthropic(api_key=api_key)
            prompt = f"""
MACRO REGIME: {macro['regime']} (Bias: {macro['bias']}, VIX: {macro['vix']:.1f})
SENTIMENT: {catalyst['overall_sentiment']} (Score: {catalyst['sentiment_score']:.2f})

TECHNICAL SETUPS ON WATCHLIST:
{json.dumps(tech, indent=2)}

CATALYSTS:
{json.dumps(catalyst['top_catalysts'], indent=2)}

Act as a Chief Prop Desk Portfolio Manager. Synthesize this data into:
1. Macro Tape Summary (2 sentences)
2. Top Actionable Setup (Include Entry Trigger, Stop Loss, Target, Risk Level)
3. Trading Risk Advisory (What to avoid today)

Format in clean markdown. Keep it punchy and direct.
"""
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            thesis_text = message.content[0].text.strip()
            
            return {
                "macro_regime": macro,
                "technical_setups": tech,
                "catalysts": catalyst,
                "trade_thesis": thesis_text
            }
            
        except Exception as e:
            log.error(f"Multi-agent synthesis failed: {e}")
            return self._build_rule_based_fallback(macro, tech, catalyst, brief)

    def _build_rule_based_fallback(self, macro: Dict, tech: List[Dict], catalyst: Dict, brief: Dict) -> Dict[str, Any]:
        """Fallback synthesis when Anthropic API key is not provided."""
        top_setup = tech[0] if tech else {"symbol": "N/A", "setup_type": "None", "change_pct": 0}
        
        thesis_text = (
            f"**Macro Tape:** Market is currently in a **{macro['regime']}** environment with VIX at {macro['vix']:.1f}. "
            f"S&P 500 Futures are {macro['sp_change_pct']:+.2f}% and Nasdaq Futures are {macro['nq_change_pct']:+.2f}%.\n\n"
            f"**Top Setup:** **{top_setup['symbol']}** ({top_setup['change_pct']:+.1f}% pre-market) — Setup: *{top_setup['setup_type']}*.\n"
            f"- **Entry Zone:** Break above Pre-Market High on 5-min ORB volume.\n"
            f"- **Stop Loss:** Below Pre-Market Low.\n"
            f"- **Risk Rating:** Medium\n\n"
            f"**Risk Advisory:** Exercise discipline around major economic releases and respect VIX levels."
        )
        
        return {
            "macro_regime": macro,
            "technical_setups": tech,
            "catalysts": catalyst,
            "trade_thesis": thesis_text
        }
