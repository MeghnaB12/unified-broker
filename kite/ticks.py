import sys
import time
import signal
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import KITE_API_KEY, KITE_WATCH_TOKENS, ALERTS, DB_PATH
from kite.auth import get_kite_client
from kiteconnect import KiteTicker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [KITE-TICKS] %(message)s")
log = logging.getLogger(__name__)

STOP_EVENT = Event()


def _init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT    NOT NULL,
            token   INTEGER NOT NULL,
            symbol  TEXT    NOT NULL,
            ltp     REAL    NOT NULL,
            volume  INTEGER,
            bid     REAL,
            ask     REAL
        )
    """)
    conn.commit()
    log.info("SQLite DB ready at %s", db_path)
    return conn


def _insert_tick(conn: sqlite3.Connection, tick: dict, symbol: str) -> None:
    depth = tick.get("depth", {})
    buy_depth  = depth.get("buy",  [{}])
    sell_depth = depth.get("sell", [{}])
    bid = buy_depth[0].get("price")  if buy_depth  else None
    ask = sell_depth[0].get("price") if sell_depth else None

    conn.execute(
        "INSERT INTO ticks (ts, token, symbol, ltp, volume, bid, ask) VALUES (?,?,?,?,?,?,?)",
        (
            datetime.utcnow().isoformat(),
            tick["instrument_token"],
            symbol,
            tick.get("last_price", 0),
            tick.get("volume"),
            bid,
            ask,
        ),
    )
    conn.commit()


_alerted: dict = {}

def _check_alerts(symbol: str, ltp: float) -> None:
    thresholds = ALERTS.get(symbol, {})

    above_key = f"{symbol}_above"
    below_key = f"{symbol}_below"

    if "above" in thresholds:
        if ltp > thresholds["above"] and not _alerted.get(above_key):
            msg = (
                f"🔔  ALERT  {symbol} crossed ABOVE ₹{thresholds['above']:.2f}"
                f"  →  LTP = ₹{ltp:.2f}"
            )
            print(f"\033[93m{msg}\033[0m", flush=True)
            log.warning(msg)
            _alerted[above_key] = True
        elif ltp <= thresholds["above"]:
            _alerted.pop(above_key, None)   # reset so alert fires again later

    if "below" in thresholds:
        if ltp < thresholds["below"] and not _alerted.get(below_key):
            msg = (
                f"🔔  ALERT  {symbol} dropped BELOW ₹{thresholds['below']:.2f}"
                f"  →  LTP = ₹{ltp:.2f}"
            )
            print(f"\033[91m{msg}\033[0m", flush=True)
            log.warning(msg)
            _alerted[below_key] = True
        elif ltp >= thresholds["below"]:
            _alerted.pop(below_key, None)


def stream_ticks(duration_seconds: int = 0) -> None:
    """
    Start the WebSocket tick stream.
    duration_seconds = 0  → run until Ctrl-C
    duration_seconds > 0  → stop after that many seconds
    """
    kite         = get_kite_client()
    access_token = kite.access_token
    conn         = _init_db(str(DB_PATH))
    tokens       = list(KITE_WATCH_TOKENS.keys())

    kws = KiteTicker(KITE_API_KEY, access_token)

    def on_ticks(ws, ticks):
        for tick in ticks:
            token  = tick["instrument_token"]
            symbol = KITE_WATCH_TOKENS.get(token, str(token))
            ltp    = tick.get("last_price", 0)
            log.info("[%-10s]  LTP = ₹%.2f", symbol, ltp)
            _insert_tick(conn, tick, symbol)
            _check_alerts(symbol, ltp)

    def on_connect(ws, response):
        log.info("WebSocket connected. Subscribing tokens: %s", tokens)
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)

    def on_close(ws, code, reason):
        log.warning("WebSocket closed — code=%s  reason=%s", code, reason)
        STOP_EVENT.set()

    def on_error(ws, code, reason):
        log.error("WebSocket error  — code=%s  reason=%s", code, reason)

    def on_reconnect(ws, attempt):
        log.info("Reconnecting… attempt #%d", attempt)

    kws.on_ticks    = on_ticks
    kws.on_connect  = on_connect
    kws.on_close    = on_close
    kws.on_error    = on_error
    kws.on_reconnect = on_reconnect

    def _sigint(sig, frame):
        log.info("Interrupt received — stopping tick stream.")
        kws.stop()
        STOP_EVENT.set()

    signal.signal(signal.SIGINT, _sigint)

    log.info("Starting tick stream: %s", KITE_WATCH_TOKENS)
    kws.connect(threaded=True)

    if duration_seconds > 0:
        STOP_EVENT.wait(timeout=duration_seconds)
        kws.stop()
    else:
        STOP_EVENT.wait()

    conn.close()
    log.info("Tick stream stopped. Tick log: %s", DB_PATH)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Kite live tick streamer")
    p.add_argument("--duration", type=int, default=0,
                   help="Seconds to run (0 = until Ctrl-C)")
    args = p.parse_args()
    stream_ticks(args.duration)
