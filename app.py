import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# -------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM STYLE
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Morning Pulse | Premarket Briefing",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to give a modern, premium dark-mode aesthetic
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
    .status-bullet {
        font-size: 1.1rem;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# HELPER DATA FUNCTIONS (Cached for Speed & Reliability)
# -------------------------------------------------------------------
@st.cache_data(ttl=300)  # Cache data for 5 minutes
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
        except:
            pulse_data[name] = {"price": 0.0, "pct": 0.0}
    return pulse_data

@st.cache_data(ttl=300)
def fetch_premarket_movers():
    """Scans a basket of highly watched retail stocks to find top premarket movers"""
    watch_basket = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "BABA", "COIN", "PLTR"]
    movers = []
    
    for ticker in watch_basket:
        try:
            t = yf.Ticker(ticker)
            # Fetch 2 days of fine-grained data including extended hours
            df = t.history(period="2d", interval="5m", prepost=True)
            if not df.empty:
                prev_close = t.info.get('previousClose', df['Close'].iloc[0])
                current_price = df['Close'].iloc[-1]
                gap_pct = ((current_price - prev_close) / prev_close) * 100
                movers.append({"Ticker": ticker, "Price": current_price, "Gap %": gap_pct})
        except:
            continue
            
    df_movers = pd.DataFrame(movers)
    if not df_movers.empty:
        return df_movers.sort_values(by="Gap %", ascending=False)
    return pd.DataFrame(columns=["Ticker", "Price", "Gap %"])

def generate_plain_english_analysis(ticker_sym):
    """Translates complex tech indicators into simple daily insights for normal folks"""
    try:
        stock = yf.Ticker(ticker_sym)
        hist = stock.history(period="200d")
        
        if len(hist) < 50:
            return {"status": "Insufficient Data", "color": "gray", "text": "Not enough history to analyze safely."}
        
        current_price = hist['Close'].iloc[-1]
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # Simple RSI Calculation
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / (loss if loss != 0 else 1)
        rsi = 100 - (100 / (1 + rs))
        
        # Translate to plain English rules
        if current_price > sma_50 and rsi < 70:
            return {
                "status": "Healthy Uptrend 🟢",
                "color": "green",
                "text": f"{ticker_sym} is showing solid upward momentum with strong institutional backing. It is not currently overextended, making it a healthy watch for today."
            }
        elif rsi >= 70:
            return {
                "status": "Extended / Overbought ⚠️",
                "color": "orange",
                "text": f"{ticker_sym} has rallied incredibly fast. Technical indicators suggest it is 'overbought' in the short term—meaning everyday buyers should exercise caution jumping in right here."
            }
        elif current_price < sma_50 and rsi > 30:
            return {
                "status": "Cooling Down 🟡",
                "color": "blue",
                "text": f"{ticker_sym} is currently experiencing a short-term pullback or consolidation phase. It is waiting for clear direction before its next big move."
            }
        elif rsi <= 30:
            return {
                "status": "Oversold / Bargain Territory 🛒",
                "color": "green",
                "text": f"{ticker_sym} has been heavily sold off recently. While risky, technical conditions indicate it is deeply oversold, which frequently attracts bounce buyers."
            }
        else:
            return {
                "status": "Caution Trend 🔴",
                "color": "red",
                "text": f"{ticker_sym} is trading below its key moving averages, signaling a macro downtrend. Use extra caution as sellers are currently in control."
            }
    except Exception as e:
        return {"status": "Analysis Unavailable", "color": "gray", "text": f"Could not compute metrics for {ticker_sym}."}

# -------------------------------------------------------------------
# APP USER INTERFACE LAYOUT
# -------------------------------------------------------------------
st.title("🌅 Morning Pulse")
st.subheader("Your 60-Second Institutional Premarket Briefing, Simplified.")
st.write(f"**Market Date:** {datetime.now().strftime('%B %d, %Y')} | Data updates automatically every 5 mins.")

st.markdown("---")

# 1. SIDEBAR - ECONOMIC CALENDAR & WATCHLISTS
with st.sidebar:
    st.header("📅 Today's Catalysts")
    st.caption("Keep an eye on these major global events moving the market today:")
    
    # Static visual calendar that can easily be mapped to an external scraper later
    st.markdown("""
    * **8:30 AM EST** - CPI Inflation Report 🔴 *(High Impact)*
    * **10:00 AM EST** - Existing Home Sales 🟡 *(Medium Impact)*
    * **2:00 PM EST** - FOMC Meeting Minutes 🔴 *(High Impact)*
    """)
    
    st.markdown("---")
    st.header("💡 Pro Tip for Everyday Folks")
    st.info("Watch the Volatility Index (VIX) on the main page. If the VIX is below 15, the market is generally calm. If it spikes above 20, expect rocky, fast-moving prices.")

# 2. MAIN LAYOUT: TOP-LEVEL METRICS (THE PULSE)
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
    # VIX drops when stocks go up, invert color designation for retail logic
    vix_status = "Calm" if vix_val < 18 else "Anxious ⚠️"
    st.metric(label=f"⚠️ Market Fear Index (VIX)", value=f"{vix_val:.2f}", delta=f"Status: {vix_status}", delta_color="off")

st.markdown("---")

# 3. TABS FOR DEEPER ANALYSIS
tab1, tab2 = st.columns([1.2, 2.0])

with tab1:
    st.header("🚀 Top Active Movers")
    st.caption("The stocks moving the most in early pre-market activity:")
    
    movers_df = fetch_premarket_movers()
    if not movers_df.empty:
        # Style dataframe for the retail viewer
        styled_df = movers_df.copy()
        styled_df["Gap %"] = styled_df["Gap %"].map("{:,.2f}%".format)
        styled_df["Price"] = styled_df["Price"].map("${:,.2f}".format)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
    else:
        st.write("No major premarket gaps detected in the primary basket right now.")

with tab2:
    st.header("🔍 Retail 'Traffic Light' Ticker Checker")
    st.caption("Type any stock ticker below to translate its massive technical data into clear, simple trading insights.")
    
    user_ticker = st.text_input("Enter Ticker (e.g., TSLA, AAPL, NVDA):", value="NVDA").upper().strip()
    
    if user_ticker:
        analysis = generate_plain_english_analysis(user_ticker)
        
        # Display clean custom status box
        st.markdown(f"### Current Condition: **{analysis['status']}**")
        st.info(analysis['text'])
        
        # Show a clean, simplified chart that isn't intimidating
        try:
            stock_data = yf.Ticker(user_ticker).history(period="30d")
            if not stock_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=stock_data.index,
                    open=stock_data['Open'],
                    high=stock_data['High'],
                    low=stock_data['Low'],
                    close=stock_data['Close'],
                    name=user_ticker
                )])
                fig.update_layout(
                    title=f"Past 30 Days Price Actions for {user_ticker}",
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=280
                )
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.error("Could not generate a preview chart for this ticker symbol.")