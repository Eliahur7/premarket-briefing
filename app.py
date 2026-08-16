import os
import re
import sys
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Ensure src modules can be imported when running streamlit run app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.exporters.tradingview import generate_pinescript, export_levels_summary
from src.ai.agents import ChiefTradingDesk, MacroAgent, TechnicalAgent

# -------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM STYLE
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Morning Pulse | Premarket Trading Desk",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark-mode trading war room aesthetic
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .metric-card {
        background-color: #1f242d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2d3440;
        text-align: center;
    }
    .badge-bull {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-bear {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# HELPER DATA FUNCTIONS (Cached for Speed)
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_market_pulse():
    """Fetches macro futures and market fear index (VIX) Data"""
    tickers = {
        "S&P 500 Futures": "^ES=F",
        "Nasdaq Futures": "^NQ=F",
        "Dow Futures": "^YM=F",
        "Volatility Index (VIX)": "^VIX"
    }
    pulse_data = {}
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                close_today = hist['Close'].iloc[-1]
                close_prev = hist['Close'].iloc[-2]
                change = close_today - close_prev
                pct_change = (change / close_prev) * 100
                pulse_data[name] = {"price": close_today, "pct": pct_change}
            else:
                pulse_data[name] = {"price": 0.0, "pct": 0.0}
        except Exception:
            pulse_data[name] = {"price": 0.0, "pct": 0.0}
    return pulse_data

@st.cache_data(ttl=300)
def fetch_sector_performance():
    """Fetches sector ETF premarket performance for institutional flow tracking"""
    sectors = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLE": "Energy",
        "XLC": "Communications",
        "XLV": "Healthcare",
        "XLI": "Industrials"
    }
    results = []
    for sym, name in sectors.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                pct = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                results.append({"Sector": name, "ETF": sym, "Change %": pct})
        except Exception:
            continue
    return pd.DataFrame(results)

@st.cache_data(ttl=300)
def fetch_premarket_movers():
    """Scans a basket of highly watched retail stocks to find top premarket movers"""
    watch_basket = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "BABA", "COIN", "PLTR"]
    movers = []
    
    for ticker in watch_basket:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="2d", interval="5m", prepost=True)
            if not df.empty:
                prev_close = t.info.get('previousClose', df['Close'].iloc[0])
                current_price = df['Close'].iloc[-1]
                gap_pct = ((current_price - prev_close) / prev_close) * 100
                high_val = df['High'].max()
                low_val = df['Low'].min()
                movers.append({
                    "Ticker": ticker,
                    "Price": current_price,
                    "Gap %": gap_pct,
                    "Pre-Market High": high_val,
                    "Pre-Market Low": low_val,
                    "Prev Close": prev_close
                })
        except Exception:
            continue
            
    df_movers = pd.DataFrame(movers)
    if not df_movers.empty:
        return df_movers.sort_values(by="Gap %", ascending=False)
    return pd.DataFrame(columns=["Ticker", "Price", "Gap %", "Pre-Market High", "Pre-Market Low", "Prev Close"])

def get_ticker_levels(ticker_sym):
    """Calculates PMH, PML, PDC, and EMAs for any symbol"""
    try:
        t = yf.Ticker(ticker_sym)
        df_ext = t.history(period="2d", interval="5m", prepost=True)
        df_daily = t.history(period="200d")
        
        if df_daily.empty:
            return None
            
        current_price = df_daily['Close'].iloc[-1]
        prev_close = df_daily['Close'].iloc[-2] if len(df_daily) >= 2 else current_price
        
        pmh = df_ext['High'].max() if not df_ext.empty else current_price * 1.01
        pml = df_ext['Low'].min() if not df_ext.empty else current_price * 0.99
        
        ema_8 = df_daily['Close'].ewm(span=8, adjust=False).mean().iloc[-1]
        ema_21 = df_daily['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
        ema_50 = df_daily['Close'].rolling(window=50).mean().iloc[-1]
        
        return {
            "symbol": ticker_sym,
            "price": current_price,
            "prev_close": prev_close,
            "premarket_change_pct": ((current_price - prev_close) / prev_close) * 100,
            "premarket_high": pmh,
            "premarket_low": pml,
            "ema_8": ema_8,
            "ema_21": ema_21,
            "ema_50": ema_50
        }
    except Exception as e:
        return None

# -------------------------------------------------------------------
# APP USER INTERFACE LAYOUT
# -------------------------------------------------------------------
st.title("🌅 Morning Pulse | Premarket Trading Desk")
st.subheader("Autonomous Multi-Agent Intelligence & TradingView Signal Exporter")
st.write(f"**Market Date:** {datetime.now().strftime('%B %d, %Y')} | Data updates live every 5 minutes.")

st.markdown("---")

# 1. SIDEBAR - ECONOMIC CALENDAR & AGENT STATUS
with st.sidebar:
    st.header("🤖 Active Trading Desk Crew")
    st.success("🟢 **Macro Regime Agent:** Online")
    st.success("🟢 **Technical Signal Agent:** Online")
    st.success("🟢 **Catalyst News Agent:** Online")
    st.success("🟢 **TradingView Exporter:** Ready")
    
    st.markdown("---")
    st.header("📅 Today's Macro Catalysts")
    st.markdown("""
    * **8:30 AM EST** - CPI Inflation Report 🔴 *(High Impact)*
    * **10:00 AM EST** - Existing Home Sales 🟡 *(Medium Impact)*
    * **2:00 PM EST** - FOMC Meeting Minutes 🔴 *(High Impact)*
    """)
    
    st.markdown("---")
    st.info("💡 **Trading Tip:** Export key levels directly into TradingView using the **PineScript Exporter** tab.")

# 2. MAIN LAYOUT: THE PULSE METRICS
pulse = fetch_market_pulse()
col1, col2, col3, col4 = st.columns(4)

with col1:
    sp_change = pulse.get("S&P 500 Futures", {"pct": 0.0})["pct"]
    st.metric(label="🇺🇸 S&P 500 Futures", 
              value=f"{pulse.get('S&P 500 Futures', {'price': 0.0})['price']:,.2f}", 
              delta=f"{sp_change:.2f}%")
with col2:
    nq_change = pulse.get("Nasdaq Futures", {"pct": 0.0})["pct"]
    st.metric(label="💻 Nasdaq 100 Futures", 
              value=f"{pulse.get('Nasdaq Futures', {'price': 0.0})['price']:,.2f}", 
              delta=f"{nq_change:.2f}%")
with col3:
    dow_change = pulse.get("Dow Futures", {"pct": 0.0})["pct"]
    st.metric(label="🏭 Dow Futures", 
              value=f"{pulse.get('Dow Futures', {'price': 0.0})['price']:,.2f}", 
              delta=f"{dow_change:.2f}%")
with col4:
    vix_val = pulse.get("Volatility Index (VIX)", {"price": 0.0})["price"]
    vix_status = "Calm" if vix_val < 18 else "Anxious ⚠️"
    st.metric(label=f"⚠️ Market Fear Index (VIX)", value=f"{vix_val:.2f}", delta=f"Status: {vix_status}", delta_color="off")

st.markdown("---")

# 3. WAR ROOM MULTI-TAB INTERFACE
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "📈 Premarket Movers & Sector Heatmap", 
    "🌲 TradingView PineScript Exporter", 
    "💬 Ask AI Premarket Analyst", 
    "🔍 Technical Chart & Traffic Light"
])

# ── TAB 1: MOVERS & SECTOR HEATMAP ──────────────────────────────────────────────
with main_tab1:
    c1, c2 = st.columns([1.5, 1.0])
    
    with c1:
        st.header("🚀 Premarket Movers Radar")
        movers_df = fetch_premarket_movers()
        if not movers_df.empty:
            display_df = movers_df[["Ticker", "Price", "Gap %", "Pre-Market High", "Pre-Market Low"]].copy()
            display_df["Gap %"] = display_df["Gap %"].map("{:,.2f}%".format)
            display_df["Price"] = display_df["Price"].map("${:,.2f}".format)
            display_df["Pre-Market High"] = display_df["Pre-Market High"].map("${:,.2f}".format)
            display_df["Pre-Market Low"] = display_df["Pre-Market Low"].map("${:,.2f}".format)
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        else:
            st.write("No major premarket gaps detected right now.")
            
    with c2:
        st.header("📊 Sector ETF Rotation")
        sector_df = fetch_sector_performance()
        if not sector_df.empty:
            fig = go.Figure(go.Bar(
                x=sector_df["Change %"],
                y=sector_df["Sector"],
                orientation='h',
                marker=dict(color=sector_df["Change %"].apply(lambda x: '#10b981' if x >= 0 else '#ef4444'))
            ))
            fig.update_layout(
                title="Sector Premarket Flow",
                template="plotly_dark",
                margin=dict(l=20, r=20, t=30, b=20),
                height=280
            )
            st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: TRADINGVIEW PINESCRIPT EXPORTER ──────────────────────────────────────
with main_tab2:
    st.header("🌲 TradingView PineScript v5 Exporter")
    st.caption("Generate PineScript v5 indicator code with Pre-Market High, Pre-Market Low, Previous Close & Gap Zones to copy-paste directly into TradingView!")
    
    col_tv1, col_tv2 = st.columns([1.2, 2.0])
    
    with col_tv1:
        selected_ticker = st.selectbox("Select Ticker to Export:", ["NVDA", "TSLA", "AMD", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "COIN", "PLTR"])
        custom_ticker = st.text_input("Or enter custom ticker:", "").upper().strip()
        
        target_symbol = custom_ticker if custom_ticker else selected_ticker
        ticker_data = get_ticker_levels(target_symbol)
        
        if ticker_data:
            st.markdown(f"### Levels for **{target_symbol}**")
            st.write(f"• **Current Price:** ${ticker_data['price']:.2f}")
            st.write(f"• **Pre-Market High:** ${ticker_data['premarket_high']:.2f}")
            st.write(f"• **Pre-Market Low:** ${ticker_data['premarket_low']:.2f}")
            st.write(f"• **Previous Close:** ${ticker_data['prev_close']:.2f}")
            st.write(f"• **50 SMA:** ${ticker_data['ema_50']:.2f}")
        else:
            st.error(f"Could not load level data for {target_symbol}")

    with col_tv2:
        if ticker_data:
            pinescript_code = generate_pinescript(target_symbol, ticker_data)
            st.markdown("### 📋 Copy TradingView PineScript Code:")
            st.code(pinescript_code, language="pinescript")
            st.caption("Copy the code above, open TradingView -> Pine Editor -> Paste & click 'Add to Chart'.")

# ── TAB 3: ASK AI PREMARKET ANALYST CHATBOT ────────────────────────────────────
with main_tab3:
    st.header("💬 Ask My Premarket AI Analyst")
    st.caption("Get instant interactive trade plan analysis, setup triggers, and risk guidance.")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Welcome to the Premarket Desk! I'm your AI Analyst. Ask me about setups, key levels, or risk on any stock today (e.g. *'What is the play on NVDA?'* or *'How does VIX at 19 impact my long trades?'*)."}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_query := st.chat_input("Ask about setups, triggers, or key levels..."):
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing market tape & technicals..."):
                # Call Anthropic if key present, else intelligent trading assistant fallback
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)
                        response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=400,
                            system="You are a sharp, senior prop-desk trader providing concise, direct advice on trade setups, key levels, and risk. No disclaimers, no hedging.",
                            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                        )
                        reply = response.content[0].text
                    except Exception as e:
                        reply = f"Error consulting AI Analyst: {e}"
                else:
                    # Smart rule-based trading analyst fallback
                    q_lower = user_query.lower()
                    found_ticker = None
                    for t in ["NVDA", "TSLA", "AMD", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "PLTR", "COIN"]:
                        if t.lower() in q_lower:
                            found_ticker = t
                            break
                            
                    if found_ticker:
                        t_data = get_ticker_levels(found_ticker)
                        if t_data:
                            reply = (
                                f"**Analysis for {found_ticker}:**\n\n"
                                f"• **Current Price:** ${t_data['price']:.2f} (Pre-market Change: {t_data['premarket_change_pct']:+.2f}%)\n"
                                f"• **Pre-Market High (PMH):** ${t_data['premarket_high']:.2f}\n"
                                f"• **Pre-Market Low (PML):** ${t_data['premarket_low']:.2f}\n\n"
                                f"🎯 **Playbook:** Watch for a 5-minute Opening Range Breakout (ORB) above **${t_data['premarket_high']:.2f}**. "
                                f"Place stop loss below PML (${t_data['premarket_low']:.2f}). If VIX remains under 20, size position normally."
                            )
                        else:
                            reply = f"I'm monitoring {found_ticker}, but market data is currently quiet. Keep an eye on its Pre-Market High breakout."
                    else:
                        reply = (
                            "**General Premarket Strategy:**\n\n"
                            "1. Focus on stocks with high **Relative Volume (RVOL > 1.5)** and clean Gap setups.\n"
                            "2. Wait for 9:30 AM ET opening bell and let the first 5-minute candle close before entering ORB setups.\n"
                            "3. Export key levels into TradingView using the **PineScript Exporter** tab to see PMH/PML lines on your chart."
                        )
                        
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

# ── TAB 4: TECHNICAL CHART & TRAFFIC LIGHT ─────────────────────────────────────
with main_tab4:
    st.header("🔍 Technical Chart & Level Overlay")
    
    chart_ticker = st.text_input("Enter Ticker for Chart Analysis:", value="NVDA", key="chart_tick_input").upper().strip()
    
    if chart_ticker:
        t_data = get_ticker_levels(chart_ticker)
        if t_data:
            c_info1, c_info2, c_info3 = st.columns(3)
            c_info1.metric("Current Price", f"${t_data['price']:.2f}", f"{t_data['premarket_change_pct']:+.2f}%")
            c_info2.metric("Pre-Market High (PMH)", f"${t_data['premarket_high']:.2f}")
            c_info3.metric("Pre-Market Low (PML)", f"${t_data['premarket_low']:.2f}")
            
            # Draw candlestick chart with overlay lines
            try:
                stock_data = yf.Ticker(chart_ticker).history(period="30d")
                if not stock_data.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=stock_data.index,
                        open=stock_data['Open'],
                        high=stock_data['High'],
                        low=stock_data['Low'],
                        close=stock_data['Close'],
                        name=chart_ticker
                    )])
                    
                    # Overlay PMH & PML lines
                    fig.add_hline(y=t_data['premarket_high'], line_dash="dash", line_color="#10b981", annotation_text="PM High")
                    fig.add_hline(y=t_data['premarket_low'], line_dash="dash", line_color="#ef4444", annotation_text="PM Low")
                    fig.add_hline(y=t_data['prev_close'], line_dash="dot", line_color="#94a3b8", annotation_text="Prev Close")
                    
                    fig.update_layout(
                        title=f"30-Day Price Action with Pre-Market Levels ({chart_ticker})",
                        template="plotly_dark",
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=20, r=20, t=40, b=20),
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Could not draw candlestick chart for {chart_ticker}: {e}")