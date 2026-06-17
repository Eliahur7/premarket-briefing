# 📈 Pre-Market Briefing Bot

An autonomous AI-powered agent that delivers a personalized pre-market intelligence digest every morning before the market opens. Combines real-time financial data, LLM-generated analysis, and AWS serverless infrastructure into a single daily briefing.

> Built by a cloud infrastructure engineer who also trades — because the best tools are the ones you build for yourself.

---

## What It Does

### Two Modes:

**📊 Interactive Dashboard (Streamlit)**
Real-time market data visualization with live futures, premarket movers, and technical analysis. Perfect for monitoring the market in real-time throughout the morning.

**📧 Scheduled Briefing (Lambda Pipeline)**
Every weekday at **7:30 AM CT**, this bot:
1. **Fetches overnight data** — futures, sector ETF pre-market moves, VIX
2. **Scans your watchlist** — checks each ticker for momentum signals, gap conditions, and news
3. **Summarizes market news** — pulls top financial headlines and runs sentiment analysis
4. **Generates a trade thesis** — Claude AI synthesizes everything into a plain-English morning brief
5. **Delivers to your inbox** — clean HTML email (or Slack, if configured)

Sample output:

```
📊 PRE-MARKET BRIEF — Tuesday, May 6, 2025 | 7:30 AM CT

MACRO PULSE
  Futures: S&P +0.4% | NQ +0.6% | VIX 18.2 (↓)
  Sector Leaders: XLK +0.8%, XLF +0.5%
  Sector Laggards: XLE -0.3%, XLU -0.1%

WATCHLIST RADAR
  🟢 NVDA  +1.8% pre  |  Gap-up above 8/21 EMA  |  Earnings beat catalyst
  🟡 AMD   +0.3% pre  |  Inside day setup        |  Watch $162 for breakout
  🔴 GOOGL -0.6% pre  |  Below VWAP pre-mkt      |  Macro ad spend concerns

AI TRADE THESIS
  The tape is setting up for a continuation day in semis. NVDA's pre-market
  gap is on above-average volume — institutional footprint visible. AMD is
  coiling. Best risk/reward: NVDA long on any 5-min ORB confirmation above
  pre-market high, stop below pre-market low. Skip GOOGL until reclaim.

  Key levels to watch: SPY 525 (support), QQQ 448 (resistance)
```

---

## Architecture

### Streamlit Dashboard
```
app.py (Streamlit)
    │
    ├──▶ yfinance → Real-time futures & movers
    └──▶ Plotly → Interactive charts & metrics
```

### Scheduled Pipeline
```
EventBridge (cron)
      │
      ▼
Lambda: orchestrator.py
      │
      ├──▶ collectors/futures.py      → Yahoo Finance / yfinance
      ├──▶ collectors/watchlist.py    → yfinance pre-market quotes
      ├──▶ collectors/news.py         → NewsAPI / RSS feeds
      │
      ├──▶ analyzers/signals.py       → Gap, momentum, EMA checks
      ├──▶ analyzers/sentiment.py     → Headline sentiment scoring
      │
      ├──▶ formatters/brief.py        → Assembles structured brief dict
      ├──▶ formatters/email_template  → Jinja2 HTML email
      │
      ├──▶ ai/thesis.py               → Anthropic Claude API call
      │
      └──▶ delivery/email.py          → AWS SES
           delivery/slack.py          → Slack webhook (optional)
```

---

## Quickstart (Local)

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/premarket-briefing.git
cd premarket-briefing
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your keys — see Configuration section below
```

### 3a. Run the Streamlit Dashboard

```bash
streamlit run app.py
```

Visit `http://localhost:8501` to see live market data with futures, movers, and technical analysis.

### 3b. Run the Scheduled Pipeline Locally

```bash
python -m src.orchestrator --dry-run
```

This prints the full brief to stdout without sending any email.

### 4. Deploy to AWS

```bash
cd infra
terraform init
terraform apply
```

---

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key |
| `NEWS_API_KEY` | [NewsAPI.org](https://newsapi.org) free tier works |
| `AWS_REGION` | e.g. `us-east-1` |
| `SES_FROM_EMAIL` | Verified SES sender address |
| `SES_TO_EMAIL` | Your delivery address |
| `SLACK_WEBHOOK_URL` | Optional — Slack incoming webhook |
| `WATCHLIST` | Comma-separated tickers e.g. `NVDA,AMD,GOOGL,MSFT` |

---

## Project Structure

```
premarket-briefing/
├── app.py                       # Streamlit interactive dashboard
├── src/
│   ├── orchestrator.py          # Lambda handler + local entrypoint
│   ├── collectors/
│   │   ├── futures.py           # Macro futures + VIX data
│   │   ├── watchlist.py         # Per-ticker pre-market data
│   │   └── news.py              # Headlines + RSS ingestion
│   ├── analyzers/
│   │   ├── signals.py           # Gap %, EMA, momentum signals
│   │   └── sentiment.py         # News sentiment scoring
│   ├── formatters/
│   │   ├── brief.py             # Assembles the brief dict
│   │   └── email_template.html  # Jinja2 HTML email
│   ├── ai/
│   │   └── thesis.py            # Claude API — trade thesis generation
│   └── delivery/
│       ├── email.py             # AWS SES delivery
│       └── slack.py             # Slack webhook delivery
├── tests/
│   ├── test_signals.py
│   ├── test_sentiment.py
│   └── test_brief.py
├── infra/
│   ├── main.tf                  # Lambda + EventBridge + IAM
│   ├── variables.tf
│   └── outputs.tf
├── docs/
│   └── sample_output.md
├── .env.example
├── requirements.txt
├── Makefile
└── README.md
```

---

## Running Tests

```bash
make test
# or
pytest tests/ -v
```

---

## Deployment Notes

- Uses **AWS Lambda** (Python 3.12 runtime) + **EventBridge** cron schedule
- Email delivery via **AWS SES** (requires verified sender domain/address)
- All secrets stored in **AWS SSM Parameter Store** (not env vars in Lambda)
- Terraform state should be stored in S3 backend for team use

### Lambda Layer

Dependencies are packaged as a Lambda layer. Build it:

```bash
make lambda-layer
```

---

## Extending It

Some ideas for v2:
- [ ] Add options flow data (unusual activity via Unusual Whales API)
- [ ] Earnings calendar integration — flag tickers reporting that day
- [ ] ThinkorSwim scan signal injection — pipe your TOS scan results in via CSV export
- [ ] Telegram delivery channel
- [ ] Web dashboard (React) showing brief history

---

## License

MIT — use it, fork it, improve it.

---

*Built with Python, AWS, and too much coffee.*
