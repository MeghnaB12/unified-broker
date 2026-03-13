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
git clone <repo-url>
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

IBKR_HOST=127.0.0.1
IBKR_PORT=7497                      # 7497=TWS paper | 7496=TWS live | 4001=Gateway
IBKR_CLIENT_ID=1

USD_INR_RATE=83.5                   # fallback rate if live FX fetch fails

ANTHROPIC_API_KEY=your_anthropic_key

ITC_ALERT_ABOVE=480.0
ONGC_ALERT_BELOW=180.0
```

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

## Task reference

| # | Task | Key file | Output |
|---|------|----------|--------|
| 1 | Kite Auth | `kite/auth.py` | Active session; token stored in `.env` |
| 2 | Kite Portfolio | `kite/portfolio.py` | DataFrames: holdings, positions, orders |
| 3 | Kite Ticks | `kite/ticks.py` | SQLite tick log; console alerts on threshold cross |
| 4 | IBKR Auth | `ibkr/auth.py` | Connected IB object; reconnect logged |
| 5 | IBKR Portfolio | `ibkr/portfolio.py` | Positions, NAV, cash; multi-currency USD + INR |
| 6 | IBKR Market Data | `ibkr/market_data.py` | CSV of mid-prices every 5 s for ≥ 60 s |
| 7 | Unified View | `unified/portfolio.py` | Single DataFrame, broker column, ₹ and $ totals |
| 8 | Dashboard | `dashboard/app.py` | Streamlit: holdings table, tick chart, broker toggle |
| 9 | AI Layer | `ai/assistant.py` | See full breakdown below |

---

## AI Layer — Task 9

`ai/assistant.py` is the differentiator. It goes beyond a simple "ask Claude a question"
wrapper by using **Claude's native tool-use (function calling)** so the model can
actively query live data rather than relying on a static context blob.

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

### CLI usage

```bash
python run.py --task 9 --brief    # 6-8 bullet daily brief (value, P&L, regime, risk)
python run.py --task 9 --risk     # detailed risk report with component breakdown
python run.py --task 9 --anomaly  # tick anomaly scan + Claude explains each spike
python run.py --task 9 --ask "What percentage of my portfolio is in Indian banking?"
python run.py --task 9            # multi-turn REPL with conversation memory
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

## Security

- `.env`, `data/`, and `logs/` are in `.gitignore` — never committed
- All access is read-only; no order placement anywhere in the codebase
- Credentials shared under NDA — do not forward or commit

---

## What I'd build next

### Short term

- **TimescaleDB tick store** — replace SQLite with TimescaleDB for efficient
  time-series queries across months of tick history; enables proper VWAP,
  rolling-window P&L, and multi-day regime analysis
- **Position reconciliation job** — nightly diff between broker-reported
  positions and local state to catch sync drift or missed fills
- **Options Greeks dashboard** — pull IV, delta, gamma for F&O positions from
  Kite and surface a live Greeks table alongside the holdings view

### Medium term

- **Rule-based alert DSL** — replace simple threshold alerts with a declarative
  rule engine: `"alert if ITC VWAP crosses 20-day SMA"` or
  `"alert if IBKR portfolio beta exceeds 1.2"`, backed by a scheduler
- **Multi-account IBKR** — fan out to multiple IBKR sub-accounts and aggregate
  under a single unified view (family office / prop desk use case)
- **Streamlit real-time mode** — swap Streamlit's polling refresh for a
  WebSocket push so the dashboard updates on every tick without a page reload

### AI differentiators (next layer)

- **Anomaly-to-news pipeline** — when `get_tick_anomalies` fires, automatically
  call a news-search tool, attach the top 3 headlines to the Claude context,
  and explain the price move with cited sources

- **Voice morning brief** — pipe `daily_brief()` output through a TTS API
  (e.g. ElevenLabs or Polly) and push as an audio notification; useful for
  pre-market prep without opening a screen

- **NL order preview** (read-only) — convert natural language like
  "show me what 10 more shares of AAPL would look like" into a structured
  position preview (cost, new weight, new risk score delta) — displayed for
  review, never submitted

- **GPT-style backtester** — feed tick history from TimescaleDB into a
  vectorbt backtest triggered by a plain-English strategy description
  ("buy ITC when z-score dips below −2, sell at +1") and surface the
  equity curve inside the dashboard

- **Conversational portfolio journal** — after each session, auto-summarise
  the REPL conversation into a dated journal entry stored locally; over time
  Claude can answer "how has my risk score trended over the past month?"
  using its own past outputs as context
