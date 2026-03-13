import sys
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
from kiteconnect import KiteConnect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kite.auth import get_kite_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [KITE-PORTFOLIO] %(message)s")
log = logging.getLogger(__name__)


def fetch_holdings(kite: KiteConnect) -> pd.DataFrame:
    """
    Returns a DataFrame of current equity holdings.
    Columns: symbol, exchange, qty, avg_cost, ltp,
             unrealised_pnl, day_change, day_change_pct,
             market_value, cost_basis
    """
    raw = kite.holdings()
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)
    cols_map = {
        "tradingsymbol":        "symbol",
        "exchange":             "exchange",
        "quantity":             "qty",
        "average_price":        "avg_cost",
        "last_price":           "ltp",
        "pnl":                  "unrealised_pnl",
        "day_change":           "day_change",
        "day_change_percentage":"day_change_pct",
    }
    df = df.rename(columns=cols_map)
    keep = [v for v in cols_map.values() if v in df.columns]
    df = df[keep].copy()

    df["market_value"] = df["qty"] * df["ltp"]
    df["cost_basis"]   = df["qty"] * df["avg_cost"]

    log.info("Holdings fetched: %d position(s)", len(df))
    return df.reset_index(drop=True)


def fetch_positions(kite: KiteConnect) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (net_df, day_df) — net (overnight) and intraday positions.
    """
    raw     = kite.positions()
    net_raw = raw.get("net", [])
    day_raw = raw.get("day", [])

    def _to_df(records):
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        cols_map = {
            "tradingsymbol": "symbol",
            "exchange":      "exchange",
            "product":       "product",
            "quantity":      "qty",
            "average_price": "avg_cost",
            "last_price":    "ltp",
            "pnl":           "unrealised_pnl",
            "value":         "market_value",
        }
        df = df.rename(columns=cols_map)
        keep = [v for v in cols_map.values() if v in df.columns]
        return df[keep].reset_index(drop=True)

    net_df = _to_df(net_raw)
    day_df = _to_df(day_raw)
    log.info("Positions — net: %d  intraday: %d", len(net_df), len(day_df))
    return net_df, day_df


def fetch_orders(kite: KiteConnect) -> pd.DataFrame:
    """Returns today's order book as a DataFrame."""
    raw = kite.orders()
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    cols_map = {
        "order_id":         "order_id",
        "tradingsymbol":    "symbol",
        "transaction_type": "side",
        "order_type":       "order_type",
        "quantity":         "qty",
        "price":            "price",
        "status":           "status",
        "order_timestamp":  "placed_at",
    }
    df = df.rename(columns=cols_map)
    keep = [v for v in cols_map.values() if v in df.columns]
    return df[keep].reset_index(drop=True)


def portfolio_summary(kite: KiteConnect) -> None:
    """Print a full portfolio snapshot to stdout."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    holdings       = fetch_holdings(kite)
    net_pos, day_pos = fetch_positions(kite)
    orders         = fetch_orders(kite)

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

    _show("Holdings", holdings)
    _show("Net Positions (Overnight)", net_pos)
    _show("Day Positions (Intraday)", day_pos)
    _show("Order Book", orders)

    if not holdings.empty:
        total_value = holdings["market_value"].sum()
        total_pnl   = holdings["unrealised_pnl"].sum()
        color = "green" if total_pnl >= 0 else "red"
        console.print(f"\n[bold green]Total Holdings Value : ₹{total_value:,.2f}[/bold green]")
        console.print(f"[bold {color}]Total Unrealised P&L : ₹{total_pnl:,.2f}[/bold {color}]")


if __name__ == "__main__":
    kite = get_kite_client()
    portfolio_summary(kite)
