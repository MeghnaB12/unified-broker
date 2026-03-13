import sys
import logging
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import USD_INR_FALLBACK

logging.basicConfig(level=logging.INFO, format="%(asctime)s [UNIFIED] %(message)s")
log = logging.getLogger(__name__)


def get_live_usd_inr() -> float:
    """
    Fetch live USD/INR rate from a public FX API.
    Falls back to the env-var static rate on failure.
    """
    import requests
    try:
        r   = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=5,
        )
        r.raise_for_status()
        rate = float(r.json()["rates"]["INR"])
        log.info("Live USD/INR = %.4f", rate)
        return rate
    except Exception as exc:
        log.warning("FX API unavailable (%s); using fallback %.4f", exc, USD_INR_FALLBACK)
        return USD_INR_FALLBACK


def build_unified_portfolio(
    kite_holdings:   pd.DataFrame,
    kite_positions:  pd.DataFrame,
    ibkr_positions:  pd.DataFrame,
    usd_inr:         float | None = None,
) -> pd.DataFrame:
    """
    Merge DataFrames from both brokers into a single unified view.

    Returns DataFrame with columns:
        broker, symbol, qty, currency, avg_cost,
        ltp, market_value_inr, market_value_usd,
        unrealised_pnl_inr, unrealised_pnl_usd
    """
    if usd_inr is None:
        usd_inr = get_live_usd_inr()

    rows = []

    if not kite_holdings.empty:
        for _, r in kite_holdings.iterrows():
            mv  = float(r.get("market_value",   r.get("qty", 0) * r.get("ltp", 0)))
            pnl = float(r.get("unrealised_pnl", 0))
            rows.append({
                "broker":             "Kite",
                "symbol":             r.get("symbol", ""),
                "qty":                r.get("qty", 0),
                "currency":           "INR",
                "avg_cost":           round(float(r.get("avg_cost", 0)), 2),
                "ltp":                round(float(r.get("ltp", 0)), 2),
                "market_value_inr":   round(mv, 2),
                "market_value_usd":   round(mv / usd_inr, 2),
                "unrealised_pnl_inr": round(pnl, 2),
                "unrealised_pnl_usd": round(pnl / usd_inr, 2),
            })

    if not kite_positions.empty:
        for _, r in kite_positions.iterrows():
            qty = r.get("qty", 0)
            if qty == 0:
                continue
            mv  = float(r.get("market_value",   qty * r.get("ltp", 0)))
            pnl = float(r.get("unrealised_pnl", 0))
            rows.append({
                "broker":             "Kite",
                "symbol":             r.get("symbol", ""),
                "qty":                qty,
                "currency":           "INR",
                "avg_cost":           round(float(r.get("avg_cost", 0)), 2),
                "ltp":                round(float(r.get("ltp", 0)), 2),
                "market_value_inr":   round(mv, 2),
                "market_value_usd":   round(mv / usd_inr, 2),
                "unrealised_pnl_inr": round(pnl, 2),
                "unrealised_pnl_usd": round(pnl / usd_inr, 2),
            })

    if not ibkr_positions.empty:
        for _, r in ibkr_positions.iterrows():
            ccy         = r.get("currency", "USD")
            mv_native   = float(r.get("mkt_value",      0))
            pnl_native  = float(r.get("unrealised_pnl", 0))

            if ccy == "USD":
                mv_inr,  pnl_inr  = mv_native * usd_inr, pnl_native * usd_inr
                mv_usd,  pnl_usd  = mv_native,            pnl_native
            elif ccy == "INR":
                mv_inr,  pnl_inr  = mv_native,            pnl_native
                mv_usd,  pnl_usd  = mv_native / usd_inr,  pnl_native / usd_inr
            else:
                # Best-effort: treat as USD
                mv_inr,  pnl_inr  = mv_native * usd_inr, pnl_native * usd_inr
                mv_usd,  pnl_usd  = mv_native,            pnl_native

            rows.append({
                "broker":             "IBKR",
                "symbol":             r.get("symbol", ""),
                "qty":                r.get("qty", 0),
                "currency":           ccy,
                "avg_cost":           round(float(r.get("avg_cost", 0)), 4),
                "ltp":                round(float(r.get("mkt_price", 0)), 4),
                "market_value_inr":   round(mv_inr,  2),
                "market_value_usd":   round(mv_usd,  2),
                "unrealised_pnl_inr": round(pnl_inr, 2),
                "unrealised_pnl_usd": round(pnl_usd, 2),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["broker", "symbol"]).reset_index(drop=True)


def print_unified_summary(df: pd.DataFrame, usd_inr: float) -> None:
    """Print a formatted unified portfolio summary with totals."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if df.empty:
        console.print("[yellow]No open positions in either broker.[/yellow]")
        return

    table = Table(title=f"Unified Portfolio Snapshot  (USD/INR = {usd_inr:.2f})",
                  show_lines=True)
    for col in df.columns:
        table.add_column(str(col), style="cyan")
    for _, row in df.iterrows():
        table.add_row(*[
            f"{v:,.2f}" if isinstance(v, (float, int)) else str(v)
            for v in row
        ])
    console.print(table)

    total_inr     = df["market_value_inr"].sum()
    total_usd     = df["market_value_usd"].sum()
    total_pnl_inr = df["unrealised_pnl_inr"].sum()
    total_pnl_usd = df["unrealised_pnl_usd"].sum()

    pnl_color = "green" if total_pnl_inr >= 0 else "red"
    by_broker = df.groupby("broker")[["market_value_inr", "market_value_usd"]].sum()

    console.print("\n[bold]── Portfolio Totals ──────────────────────────────────────[/bold]")
    console.print(
        f"  Total Value      :  [bold green]₹{total_inr:>14,.2f}[/bold green]"
        f"  /  [bold blue]${total_usd:>12,.2f}[/bold blue]"
    )
    console.print(
        f"  Unrealised P&L   :  "
        f"[bold {pnl_color}]₹{total_pnl_inr:>14,.2f}[/bold {pnl_color}]"
        f"  /  [bold {pnl_color}]${total_pnl_usd:>12,.2f}[/bold {pnl_color}]"
    )
    console.print("\n[bold]── By Broker ─────────────────────────────────────────────[/bold]")
    for broker, vals in by_broker.iterrows():
        console.print(
            f"  {broker:<8}       :  ₹{vals['market_value_inr']:>14,.2f}"
            f"  /  ${vals['market_value_usd']:>12,.2f}"
        )


if __name__ == "__main__":
    from kite.auth       import get_kite_client
    from kite.portfolio  import fetch_holdings, fetch_positions as kite_fetch_positions
    from ibkr.auth       import get_ibkr_client
    from ibkr.portfolio  import fetch_positions as ibkr_fetch_positions

    kite          = get_kite_client()
    kite_holdings = fetch_holdings(kite)
    kite_net, _   = kite_fetch_positions(kite)

    ib       = get_ibkr_client()
    ibkr_pos = ibkr_fetch_positions(ib)
    ib.disconnect()

    usd_inr = get_live_usd_inr()
    unified = build_unified_portfolio(kite_holdings, kite_net, ibkr_pos, usd_inr)
    print_unified_summary(unified, usd_inr)
