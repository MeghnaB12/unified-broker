# Unified Broker

A unified data layer connecting **Zerodha Kite** (Indian equities / F&O) and
**Interactive Brokers** (US / global equities) with a Streamlit dashboard and
a Claude-powered AI portfolio intelligence layer.

---

## Architecture

```
unified-broker/
├── kite/
│   ├── auth.py          # OAuth 2.0 login, token refresh, session guard
│   ├── portfolio.py     # Holdings, overnight + intraday positions, order book → DataFrames
│   └── ticks.py         # WebSocket tick stream → SQLite + threshold alerts
├── ibkr/
│   ├── auth.py          # ib_insync connect, exponential back-off reconnect
│   ├── portfolio.py     # Positions, NAV, cash, unrealised P&L, multi-currency
│   └── market_data.py   # Live quotes (AAPL/MSFT/GOOGL) → CSV every 5 s
├── unified/
│   └── portfolio.py     # Merge Kite + IBKR, live FX rate, dual INR/USD totals
├── dashboard/
│   └── app.py           # Streamlit UI — holdings table, tick chart, broker toggle
├── ai/
│   └── assistant.py     # Claude tool-use, risk scorer, regime detector, NL Q&A
├── run.py               # CLI entry point for all 9 tasks
├── generate_report.py   # Builds the implementation PDF report
└── requirements.txt     # Python dependencies
```

### Data flow

```
Kite REST API ──► kite/portfolio.py ─────┐
Kite WebSocket ──► kite/ticks.py ─────── ┤
                                          ├──► unified/portfolio.py ──► dashboard
IBKR TWS/Gateway ──► ibkr/portfolio.py ──┤                               │
IBKR Market Data ──► ibkr/market_data ───┘                               │
                                                                          ▼
                                                                    ai/assistant.py
                                                                 (Claude tool-use)
```

---

## Requirements

- Python 3.10+
- Zerodha Kite Connect API app (`api_key` + `api_secret`)
- IBKR TWS or IB Gateway running locally
- Anthropic API key (Task 9 AI layer)

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/MeghnaB12/unified-broker.git
cd unified-broker
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

Create a `.env` file in the project root:

```env
KITE_API_KEY=your_kite_api_key
KITE_API_SECRET=your_kite_api_secret
KITE_ACCESS_TOKEN=                  # auto-filled after first login
                                    # Session token is persisted to .env for convenience during the dev phase

IBKR_HOST=127.0.0.1
IBKR_PORT=7497                      # 7497=TWS paper | 7496=TWS live | 4001=Gateway
IBKR_CLIENT_ID=1

USD_INR_RATE=83.5                   # fallback rate if live FX fetch fails

ANTHROPIC_API_KEY=your_anthropic_key

ITC_ALERT_ABOVE=480.0
ONGC_ALERT_BELOW=180.0
```

---

## IBKR setup note

Before running Tasks 4–6:

1. Open TWS or IB Gateway
2. **Edit → Global Configuration → API → Settings**
3. Enable **"Enable ActiveX and Socket Clients"**
4. Socket port: `7497` (paper) or `7496` (live)
5. Add `127.0.0.1` to trusted IPs

---

## Run with live credentials

```bash
# Task 1 — Kite login (opens browser; paste request_token from redirect URL)
python run.py --task 1

# Task 2 — Live Kite portfolio
python run.py --task 2

# Task 3 — Tick stream: ITC, ONGC, NIFTY 50 for 60 s
python run.py --task 3 --duration 60

# Task 4 — IBKR connect + reconnect test (requires TWS/Gateway running)
python run.py --task 4

# Task 5 — IBKR live portfolio
python run.py --task 5

# Task 6 — IBKR mid-prices to CSV for 60 s
python run.py --task 6 --duration 60

# Task 7 — Unified Kite + IBKR view with dual-currency totals
python run.py --task 7

# Task 8 — Streamlit dashboard (→ http://localhost:8501)
python run.py --task 8

# Task 9 — AI layer
python run.py --task 9 --ask "What is my tech sector exposure?"
python run.py --task 9 --brief      # plain-English daily brief
python run.py --task 9 --risk       # portfolio risk report
python run.py --task 9 --anomaly    # tick anomaly scan + Claude explanation
python run.py --task 9              # interactive multi-turn REPL
```

---

### How tool-use works here

```
User question
     │
     ▼
Claude decides which tool(s) to call
     │
     ├── get_positions(broker="Kite")
     ├── get_pnl_summary()
     ├── get_sector_exposure()
     ├── get_risk_score()
     ├── get_tick_anomalies(z_threshold=3.0)
     └── get_market_regime()
     │
     ▼
Tool results returned to Claude
     │
     ▼
Claude composes a grounded, accurate answer
```

Claude decides which tools to call, in what order, and how to synthesise the
results — making every answer computed from real data rather than hallucinated.

### Available tools

| Tool | What it does |
|------|-------------|
| `get_positions` | Fetches live positions, optionally filtered by broker |
| `get_pnl_summary` | Total unrealised P&L in ₹ and $, top gainer, top loser, by-broker split |
| `get_sector_exposure` | Sector allocation (Technology, Banking, Energy, …) with % weight |
| `get_risk_score` | 0–100 risk score using HHI concentration, broker split, drawdown |
| `get_tick_anomalies` | Z-score scan of SQLite tick DB; flags SPIKE ▲ / DIP ▼ |
| `get_market_regime` | Classifies recent tick volatility: TRENDING / RANGING / HIGH-VOL |

### Portfolio risk scorer

The risk score is a weighted composite of five signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| Position HHI | 35% | Herfindahl-Hirschman Index across individual holdings |
| Sector HHI | 25% | HHI across sector buckets |
| Broker split | 20% | Penalty for >80% concentration at one broker |
| Largest single loss | 10% | Biggest losing position as % of total value |
| Total drawdown | 10% | Sum of all unrealised losses / market value |

Score 0–24 = **LOW** · 25–49 = **MODERATE** · 50–74 = **HIGH** · 75–100 = **VERY HIGH**

```bash
python run.py --task 9 --risk
# → Risk score: 31/100 (MODERATE)
#   Position HHI = 18.4 — reasonably diversified across 8 stocks
#   Sector HHI = 42.1 — Technology is dominant at 55% of portfolio
#   Broker split HHI = 61.0 — 78% held at Kite; consider rebalancing
#   Largest single loss: HDFCBANK −₹339 (0.4% of portfolio)
```

### Market regime detector

Reads the live tick SQLite DB and classifies conditions using rolling z-score
dispersion and linear trend slope per symbol:

- **TRENDING** — consistent directional drift (avg slope > 0.05)
- **RANGING** — low z-score dispersion, no clear direction
- **HIGH-VOLATILITY** — median |z| > 1.5 across symbols

The regime is surfaced automatically in the daily brief.

### Multi-turn conversational REPL

The interactive REPL keeps a full message history so Claude can refer back to
previous answers within a session:

```
You › What is my risk score?
Claude › Risk score: 31/100 (MODERATE). Technology is your top concentration...

You › Which stocks are driving that?
Claude › The main contributors to your Technology exposure are TCS (18%), INFY (12%)...

You › And how does that compare to my IBKR positions?
Claude › Your IBKR book adds AAPL, MSFT, GOOGL — all Technology...
```

---

