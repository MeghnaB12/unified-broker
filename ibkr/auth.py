import sys
import time
import logging
from pathlib import Path

import ib_insync

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [IBKR-AUTH] %(message)s")
log = logging.getLogger(__name__)

MAX_RETRIES  = 5
RETRY_DELAY  = 5   # base seconds between retries


def get_ibkr_client(
    host:       str = IBKR_HOST,
    port:       int = IBKR_PORT,
    client_id:  int = IBKR_CLIENT_ID,
    max_retries: int = MAX_RETRIES,
) -> ib_insync.IB:
    """
    Return a connected ib_insync.IB instance.

    Retries up to `max_retries` times with exponential back-off.
    A disconnect handler is attached so the client attempts to
    reconnect automatically after an unexpected drop.
    """
    ib = ib_insync.IB()
    _attach_handlers(ib, host, port, client_id)

    delay = RETRY_DELAY
    for attempt in range(1, max_retries + 1):
        try:
            ib.connect(host, port, clientId=client_id, timeout=15)
            log.info(
                "Connected to IBKR — host=%s  port=%d  clientId=%d  [attempt %d/%d]",
                host, port, client_id, attempt, max_retries,
            )
            _log_account_info(ib)
            return ib
        except Exception as exc:
            log.warning("Attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                log.info("Retrying in %ds…", delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)   # cap at 60 s
            else:
                raise RuntimeError(
                    f"Could not connect to IBKR after {max_retries} attempts.\n"
                    "Ensure TWS or IB Gateway is running and API access is enabled\n"
                    f"  Settings → API → Enable ActiveX and Socket Clients  (port {port})"
                ) from exc

    return ib  # unreachable; satisfies type checkers


def _attach_handlers(ib: ib_insync.IB, host: str, port: int, client_id: int) -> None:
    """Register error and disconnect event callbacks."""

    def _on_disconnected():
        log.warning("IBKR connection lost. Auto-reconnect in %ds…", RETRY_DELAY)
        time.sleep(RETRY_DELAY)
        try:
            ib.connect(host, port, clientId=client_id, timeout=15)
            log.info("Reconnected to IBKR successfully.")
        except Exception as exc:
            log.error("Auto-reconnect failed: %s", exc)

    def _on_error(req_id, error_code, error_string, contract):
        # 2104/2106/2158/2119 are informational "data farm connected" notices
        informational = {2100, 2104, 2106, 2107, 2108, 2119, 2157, 2158}
        if error_code in informational:
            log.debug("IBKR [info %d]: %s", error_code, error_string)
        else:
            log.error(
                "IBKR error [reqId=%s  code=%d]: %s",
                req_id, error_code, error_string,
            )

    ib.disconnectedEvent += _on_disconnected
    ib.errorEvent        += _on_error


def _log_account_info(ib: ib_insync.IB) -> None:
    """Log basic account info to confirm the session is live."""
    accounts = ib.managedAccounts()
    log.info("Managed accounts: %s", accounts)
    if accounts:
        summary = ib.accountSummary(accounts[0])
        nav = next(
            (s.value for s in summary if s.tag == "NetLiquidation"), "N/A"
        )
        ccy = next(
            (s.currency for s in summary if s.tag == "NetLiquidation"), ""
        )
        log.info("Account NAV: %s %s", nav, ccy)


if __name__ == "__main__":
    ib = get_ibkr_client()
    print(f"\n✓ Connected to IBKR TWS / Gateway")
    print(f"  Server version : {ib.client.serverVersion()}")
    print(f"  Managed accts  : {ib.managedAccounts()}")

    print("\n  [reconnect test] Disconnecting…")
    ib.disconnect()
    time.sleep(3)
    print("  Reconnecting via get_ibkr_client()…")
    ib2 = get_ibkr_client()
    print(f"  Reconnected ✓  accounts={ib2.managedAccounts()}")
    ib2.disconnect()
    print("  Disconnected cleanly.")
