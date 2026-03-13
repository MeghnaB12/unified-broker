import sys
import csv
import time
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path

import ib_insync

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import IBKR_WATCH_SYMBOLS, IBKR_CSV

logging.basicConfig(level=logging.INFO, format="%(asctime)s [IBKR-DATA] %(message)s")
log = logging.getLogger(__name__)

SAMPLE_INTERVAL = 5    # seconds between CSV rows
RUN_DURATION    = 60   # minimum run time in seconds


def stream_market_data(
    symbols:  list = None,
    duration: int  = RUN_DURATION,
    csv_path: str  = str(IBKR_CSV),
) -> None:
    """
    Stream live mid-prices for `symbols` to `csv_path` for `duration` seconds.

    CSV columns: timestamp, symbol, bid, ask, mid_price
    """
    if symbols is None:
        symbols = IBKR_WATCH_SYMBOLS

    from ibkr.auth import get_ibkr_client
    ib = get_ibkr_client()

    contracts = [ib_insync.Stock(sym, "SMART", "USD") for sym in symbols]
    ib.qualifyContracts(*contracts)

    tickers: dict[str, ib_insync.Ticker] = {
        c.symbol: ib.reqMktData(c, "", False, False) for c in contracts
    }
    log.info("Subscribed to live market data: %s", symbols)
    ib.sleep(2)   # allow first snapshot to arrive

    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_file.exists() or csv_file.stat().st_size == 0

    stop = False

    def _sigint(sig, frame):
        nonlocal stop
        log.info("Interrupt — stopping market data stream.")
        stop = True

    signal.signal(signal.SIGINT, _sigint)

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "symbol", "bid", "ask", "mid_price"])

        end_time = time.time() + duration
        while time.time() < end_time and not stop:
            ts = datetime.now(timezone.utc).isoformat()
            for sym, ticker in tickers.items():
                bid = ticker.bid  if (ticker.bid  and ticker.bid  > 0) else None
                ask = ticker.ask  if (ticker.ask  and ticker.ask  > 0) else None
                mid = round((bid + ask) / 2, 4) if (bid and ask) else None
                writer.writerow([ts, sym, bid, ask, mid])
                log.info(
                    "[%-6s]  bid=%s  ask=%s  mid=%s",
                    sym,
                    f"{bid:.4f}" if bid else "N/A",
                    f"{ask:.4f}" if ask else "N/A",
                    f"{mid:.4f}" if mid else "N/A",
                )
            f.flush()
            ib.sleep(SAMPLE_INTERVAL)

    for c in contracts:
        try:
            ib.cancelMktData(c)
        except Exception:
            pass

    ib.disconnect()
    log.info("Market data stream complete.  CSV → %s", csv_path)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="IBKR live market data streamer")
    p.add_argument("--duration", type=int, default=RUN_DURATION,
                   help=f"Seconds to run (default {RUN_DURATION})")
    p.add_argument("--symbols", nargs="+", default=IBKR_WATCH_SYMBOLS,
                   help="Ticker symbols (default: AAPL MSFT GOOGL)")
    args = p.parse_args()
    stream_market_data(symbols=args.symbols, duration=args.duration)
