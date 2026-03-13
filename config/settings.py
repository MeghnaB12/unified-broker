"""Central configuration — reads from environment / .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Zerodha ──────────────────────────────────────────────────────────────────
KITE_API_KEY      = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET   = os.getenv("KITE_API_SECRET", "")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")

# ── IBKR ─────────────────────────────────────────────────────────────────────
IBKR_HOST      = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT      = int(os.getenv("IBKR_PORT", 7497))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", 1))

# ── FX ───────────────────────────────────────────────────────────────────────
USD_INR_FALLBACK = float(os.getenv("USD_INR_RATE", 83.5))

# ── AI ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Alert thresholds ─────────────────────────────────────────────────────────
ALERTS = {
    "ITC":  {"above": float(os.getenv("ITC_ALERT_ABOVE",  480.0))},
    "ONGC": {"below": float(os.getenv("ONGC_ALERT_BELOW", 180.0))},
}

# ── Kite instrument tokens (NSE) ──────────────────────────────────────────────
KITE_WATCH_TOKENS = {
    424961:  "ITC",
    633601:  "ONGC",
    256265:  "NIFTY 50",
}

# ── IBKR watchlist ────────────────────────────────────────────────────────────
IBKR_WATCH_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]

# ── Data paths ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
LOGS_DIR   = BASE_DIR / "logs"
DB_PATH    = DATA_DIR / "ticks.db"
IBKR_CSV   = LOGS_DIR / "ibkr_midprice.csv"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
