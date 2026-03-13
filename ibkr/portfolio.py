import sys
import logging
from pathlib import Path

import pandas as pd
import ib_insync

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import USD_INR_FALLBACK

logging.basicConfig(level=logging.INFO, format="%(asctime)s [IBKR-PORTFOLIO] %(message)s")
log = logging.getLogger(__name__)


def get_usd_inr_rate(ib: ib_insync.IB) -> float:
    """
    Fetch live USD/INR FX rate via IBKR market data.
    Falls back to the static env-var rate on any error.
    """
    try:
        fx = ib_insync.Forex("USDINR")
        ib.qualifyContracts(fx)
        ticker = ib.reqMktData(fx, "", False, False)
        ib.sleep(2)
        if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
            mid = (ticker.bid + ticker.ask) / 2
            ib.cancelMktData(fx)
            log.info("Live USD/INR rate from IBKR: %.4f", mid)
            return mid
        ib.cancelMktData(fx)
    except Exception as exc:
        log.debug("IBKR FX fetch failed (%s); using fallback.", exc)

    log.info("Using fallback USD/INR rate: %.4f", USD_INR_FALLBACK)
    return USD_INR_FALLBACK


def fetch_positions(ib: ib_insync.IB) -> pd.DataFrame:
    """
    Returns all open IBKR positions as a DataFrame.
    Columns: broker, symbol, sec_type, exchange, currency,
             qty, avg_cost, mkt_price, mkt_value,
             unrealised_pnl, inr_equiv
    """
    usd_inr = get_usd_inr_rate(ib)
    rows = []

    for pos in ib.portfolio():
        c        = pos.contract
        currency = c.currency
        mv       = pos.marketValue
        pnl      = pos.unrealizedPNL

        if currency == "USD":
            inr_equiv = mv * usd_inr
        elif currency == "INR":
            inr_equiv = mv
        else:
            inr_equiv = None

        rows.append({
            "broker":         "IBKR",
            "symbol":         c.symbol,
            "sec_type":       c.secType,
            "exchange":       c.exchange,
            "currency":       currency,
            "qty":            pos.position,
            "avg_cost":       round(pos.averageCost, 4),
            "mkt_price":      round(pos.marketPrice,  4),
            "mkt_value":      round(mv,  2),
            "unrealised_pnl": round(pnl, 2),
            "inr_equiv":      round(inr_equiv, 2) if inr_equiv is not None else None,
        })

    df = pd.DataFrame(rows)
    log.info(
        "Fetched %d IBKR position(s). USD/INR used: %.4f",
        len(df), usd_inr,
    )
    return df


def fetch_account_summary(ib: ib_insync.IB) -> pd.DataFrame:
    """Returns key account metrics across all managed accounts."""
    accounts = ib.managedAccounts()
    TAGS = {
        "NetLiquidation", "TotalCashValue",
        "UnrealizedPnL",  "RealizedPnL",
        "GrossPositionValue", "MaintMarginReq",
    }
    rows = []
    for acct in accounts:
        for s in ib.accountSummary(acct):
            if s.tag in TAGS:
                rows.append({
                    "account":  acct,
                    "tag":      s.tag,
                    "value":    s.value,
                    "currency": s.currency,
                })
    return pd.DataFrame(rows)


def portfolio_summary(ib: ib_insync.IB) -> None:
    """Print a full IBKR portfolio snapshot using rich tables."""
    from rich.console import Console
    from rich.table import Table

    console   = Console()
    positions = fetch_positions(ib)
    account   = fetch_account_summary(ib)

    def _show(title: str, df: pd.DataFrame):
        if df.empty:
            console.print(f"[yellow]{title}: (empty)[/yellow]")
            return
        table = Table(title=title, show_lines=True)
        for col in df.columns:
            table.add_column(str(col), style="cyan")
        for _, row in df.iterrows():
            table.add_row(*[
                f"{v:,.2f}" if isinstance(v, float) else str(v)
                for v in row
            ])
        console.print(table)

    _show("IBKR Positions", positions)
    _show("Account Summary", account)

    if not positions.empty:
        total_pnl = positions["unrealised_pnl"].sum()
        total_inr = positions["inr_equiv"].dropna().sum()
        color = "green" if total_pnl >= 0 else "red"
        console.print(f"\n[bold {color}]Total Unrealised P&L : ${total_pnl:,.2f}[/bold {color}]")
        console.print(f"[bold cyan]Portfolio INR equiv  : ₹{total_inr:,.2f}[/bold cyan]")


if __name__ == "__main__":
    from ibkr.auth import get_ibkr_client
    ib = get_ibkr_client()
    portfolio_summary(ib)
    ib.disconnect()
