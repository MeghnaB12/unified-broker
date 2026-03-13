import json
import logging
import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import ANTHROPIC_API_KEY, DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AI] %(message)s")
log = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"

SECTOR_MAP: dict[str, str] = {
    # Kite / NSE
    "RELIANCE":  "Energy",
    "ONGC":      "Energy",
    "TCS":       "Technology",
    "INFY":      "Technology",
    "WIPRO":     "Technology",
    "HCLTECH":   "Technology",
    "HDFCBANK":  "Banking",
    "ICICIBANK": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK":  "Banking",
    "ITC":       "FMCG",
    "HINDUNILVR":"FMCG",
    "MARUTI":    "Auto",
    "TATAMOTORS":"Auto",
    "BAJFINANCE":"NBFC",
    # IBKR / US
    "AAPL":      "Technology",
    "MSFT":      "Technology",
    "GOOGL":     "Technology",
    "AMZN":      "Consumer",
    "META":      "Technology",
    "TSLA":      "Auto",
    "NVDA":      "Technology",
    "JPM":       "Banking",
    "BAC":       "Banking",
    "XOM":       "Energy",
}


def _get_claude():
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _load_portfolio() -> dict:
    """
    Load unified portfolio from both brokers.
    Falls back gracefully if either broker is unavailable.
    Returns dict: unified_df, usd_inr, kite_orders.
    """
    from unified.portfolio import build_unified_portfolio, get_live_usd_inr

    usd_inr = get_live_usd_inr()
    kite_holdings = kite_net = ibkr_pos = kite_orders = pd.DataFrame()

    try:
        from kite.auth      import get_kite_client
        from kite.portfolio import fetch_holdings, fetch_positions, fetch_orders
        kite          = get_kite_client()
        kite_holdings = fetch_holdings(kite)
        kite_net, _   = fetch_positions(kite)
        kite_orders   = fetch_orders(kite)
        log.info("Kite data loaded.")
    except Exception as exc:
        log.warning("Could not load Kite data: %s", exc)

    try:
        from ibkr.auth      import get_ibkr_client
        from ibkr.portfolio import fetch_positions as ibkr_fetch
        ib       = get_ibkr_client()
        ibkr_pos = ibkr_fetch(ib)
        ib.disconnect()
        log.info("IBKR data loaded.")
    except Exception as exc:
        log.warning("Could not load IBKR data: %s", exc)

    unified = build_unified_portfolio(kite_holdings, kite_net, ibkr_pos, usd_inr)
    return {"unified_df": unified, "usd_inr": usd_inr, "kite_orders": kite_orders}


def _tool_get_positions(portfolio_data: dict, broker: str = "all") -> dict:
    """Return positions, optionally filtered by broker."""
    df = portfolio_data["unified_df"]
    if df.empty:
        return {"positions": []}
    if broker.lower() != "all":
        df = df[df["broker"].str.lower() == broker.lower()]
    return {"positions": df.to_dict(orient="records")}


def _tool_get_pnl_summary(portfolio_data: dict) -> dict:
    """Return P&L totals broken down by broker and currency."""
    df      = portfolio_data["unified_df"]
    usd_inr = portfolio_data["usd_inr"]
    if df.empty:
        return {"total_inr": 0, "total_usd": 0, "by_broker": {}}

    total_inr     = float(df.get("unrealised_pnl_inr", pd.Series([0])).sum())
    total_usd     = total_inr / usd_inr if usd_inr else 0
    market_val    = float(df.get("market_value_inr", pd.Series([0])).sum())

    by_broker: dict[str, Any] = {}
    for broker, grp in df.groupby("broker"):
        pnl_inr = float(grp.get("unrealised_pnl_inr", pd.Series([0])).sum())
        by_broker[broker] = {
            "unrealised_pnl_inr": round(pnl_inr, 2),
            "unrealised_pnl_usd": round(pnl_inr / usd_inr, 2) if usd_inr else 0,
        }

    return {
        "total_unrealised_pnl_inr": round(total_inr, 2),
        "total_unrealised_pnl_usd": round(total_usd, 2),
        "total_market_value_inr":   round(market_val, 2),
        "usd_inr_rate":             usd_inr,
        "by_broker":                by_broker,
        "top_gainer": (
            df.loc[df["unrealised_pnl_inr"].idxmax(), ["symbol", "unrealised_pnl_inr"]].to_dict()
            if "unrealised_pnl_inr" in df.columns and not df.empty else {}
        ),
        "top_loser": (
            df.loc[df["unrealised_pnl_inr"].idxmin(), ["symbol", "unrealised_pnl_inr"]].to_dict()
            if "unrealised_pnl_inr" in df.columns and not df.empty else {}
        ),
    }


def _tool_get_sector_exposure(portfolio_data: dict) -> dict:
    """Return portfolio weight by sector (INR-normalised)."""
    df = portfolio_data["unified_df"]
    if df.empty or "market_value_inr" not in df.columns:
        return {"sectors": {}}

    df = df.copy()
    df["sector"] = df["symbol"].map(SECTOR_MAP).fillna("Other")
    total = df["market_value_inr"].sum()
    by_sector: dict[str, Any] = {}
    for sector, grp in df.groupby("sector"):
        val = float(grp["market_value_inr"].sum())
        by_sector[sector] = {
            "market_value_inr": round(val, 2),
            "weight_pct":       round(100 * val / total, 2) if total else 0,
            "symbols":          grp["symbol"].tolist(),
        }
    return {"sectors": by_sector, "total_market_value_inr": round(float(total), 2)}


def _tool_get_risk_score(portfolio_data: dict) -> dict:
    """
    Compute a 0-100 portfolio risk score.

    Components
    ──────────
    • Concentration (HHI)       — 0=diversified, 100=single position
    • Broker split              — penalty if >80% with one broker
    • Sector concentration      — HHI across sectors
    • Largest single drawdown   — % of portfolio in one losing position
    • Total drawdown ratio      — total unrealised loss / market value

    Lower score = lower risk.
    """
    df      = portfolio_data["unified_df"]
    usd_inr = portfolio_data["usd_inr"]

    if df.empty or "market_value_inr" not in df.columns:
        return {"risk_score": None, "reason": "No position data available."}

    total_val = df["market_value_inr"].sum()
    if total_val == 0:
        return {"risk_score": None, "reason": "Zero market value."}

    weights = df["market_value_inr"] / total_val

    hhi_position = float((weights ** 2).sum() * 100)

    broker_weights = df.groupby("broker")["market_value_inr"].sum() / total_val
    hhi_broker = float((broker_weights ** 2).sum() * 100)

    df2 = df.copy()
    df2["sector"] = df2["symbol"].map(SECTOR_MAP).fillna("Other")
    sector_weights = df2.groupby("sector")["market_value_inr"].sum() / total_val
    hhi_sector = float((sector_weights ** 2).sum() * 100)

    if "unrealised_pnl_inr" in df.columns:
        losses      = df[df["unrealised_pnl_inr"] < 0]["unrealised_pnl_inr"]
        max_loss    = float(losses.min()) if not losses.empty else 0.0
        loss_ratio  = abs(max_loss) / total_val * 100
        total_loss  = float(df["unrealised_pnl_inr"].clip(upper=0).sum())
        total_drawdown_ratio = abs(total_loss) / total_val * 100
    else:
        loss_ratio = total_drawdown_ratio = 0.0

    score = (
        hhi_position          * 0.35 +
        hhi_broker            * 0.20 +
        hhi_sector            * 0.25 +
        min(loss_ratio, 100)  * 0.10 +
        min(total_drawdown_ratio, 100) * 0.10
    )
    score = min(100, round(score, 1))

    if score < 25:
        label = "LOW"
    elif score < 50:
        label = "MODERATE"
    elif score < 75:
        label = "HIGH"
    else:
        label = "VERY HIGH"

    return {
        "risk_score":             score,
        "risk_label":             label,
        "hhi_position":           round(hhi_position, 2),
        "hhi_broker":             round(hhi_broker, 2),
        "hhi_sector":             round(hhi_sector, 2),
        "largest_loss_pct":       round(loss_ratio, 2),
        "total_drawdown_pct":     round(total_drawdown_ratio, 2),
        "num_positions":          len(df),
        "interpretation": (
            f"Risk score {score}/100 ({label}). "
            f"Position concentration (HHI) = {hhi_position:.1f}, "
            f"sector concentration = {hhi_sector:.1f}, "
            f"broker split = {hhi_broker:.1f}."
        ),
    }


def _tool_get_tick_anomalies(
    db_path: str       = str(DB_PATH),
    z_threshold: float = 2.5,
    lookback_rows: int = 100,
) -> dict:
    """Scan tick DB for price anomalies; returns list of flagged symbols."""
    anomalies = detect_tick_anomalies(db_path, z_threshold, lookback_rows)
    if anomalies.empty:
        return {"anomalies": [], "count": 0}
    return {
        "anomalies": anomalies.to_dict(orient="records"),
        "count":     len(anomalies),
    }


def _tool_get_market_regime(
    db_path: str       = str(DB_PATH),
    lookback_rows: int = 200,
) -> dict:
    """
    Classify recent market regime from tick volatility.

    Method: compute rolling z-score of LTP per symbol. If median |z| is high
    → HIGH-VOL; if mean price direction is consistent → TRENDING; else RANGING.
    """
    if not Path(db_path).exists():
        return {"regime": "UNKNOWN", "reason": "No tick data."}

    conn = sqlite3.connect(db_path)
    df   = pd.read_sql_query(
        f"SELECT symbol, ltp, ts FROM ticks ORDER BY id DESC LIMIT {lookback_rows * 5}",
        conn,
    )
    conn.close()

    if df.empty or len(df) < 20:
        return {"regime": "UNKNOWN", "reason": "Insufficient tick data."}

    results: list[dict] = []
    for sym, grp in df.groupby("symbol"):
        if len(grp) < 10:
            continue
        prices = grp["ltp"].values[::-1]          # chronological order
        z      = (prices - prices.mean()) / (prices.std() or 1)
        median_abs_z = float(np.median(np.abs(z)))
        direction    = float(np.polyfit(range(len(prices)), prices, 1)[0])
        results.append({
            "symbol":       sym,
            "median_abs_z": round(median_abs_z, 3),
            "trend_slope":  round(direction, 4),
        })

    if not results:
        return {"regime": "UNKNOWN", "reason": "No usable symbols."}

    avg_z     = np.mean([r["median_abs_z"] for r in results])
    avg_slope = np.mean([abs(r["trend_slope"]) for r in results])

    if avg_z > 1.5:
        regime = "HIGH-VOLATILITY"
    elif avg_slope > 0.05:
        regime = "TRENDING"
    else:
        regime = "RANGING"

    return {
        "regime":     regime,
        "avg_z":      round(float(avg_z), 3),
        "avg_slope":  round(float(avg_slope), 5),
        "per_symbol": results,
    }


TOOLS = [
    {
        "name": "get_positions",
        "description": (
            "Fetch current portfolio positions from both brokers. "
            "Optionally filter by broker name ('Kite' or 'IBKR'). "
            "Returns symbol, qty, avg_cost, ltp, unrealised_pnl, currency, broker."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "broker": {
                    "type": "string",
                    "enum": ["all", "Kite", "IBKR"],
                    "description": "Which broker to filter by. Default: 'all'.",
                }
            },
        },
    },
    {
        "name": "get_pnl_summary",
        "description": (
            "Get a full P&L breakdown: total unrealised P&L in INR and USD, "
            "market value, top gainer and top loser, split by broker."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sector_exposure",
        "description": (
            "Return portfolio allocation by sector (Technology, Banking, Energy, etc.) "
            "with market value in INR and percentage weight."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_risk_score",
        "description": (
            "Compute a 0-100 portfolio risk score using concentration (HHI), "
            "broker split, sector exposure, and unrealised drawdown. "
            "Returns score, label (LOW/MODERATE/HIGH/VERY HIGH), and component breakdown."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_tick_anomalies",
        "description": (
            "Scan the live tick database for price anomalies using z-score. "
            "Returns any symbols whose latest LTP deviates significantly from "
            "the rolling mean, with direction (SPIKE ▲ / DIP ▼)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "z_threshold": {
                    "type": "number",
                    "description": "Standard deviation threshold. Default: 2.5.",
                }
            },
        },
    },
    {
        "name": "get_market_regime",
        "description": (
            "Classify current market regime from recent tick data as one of: "
            "TRENDING, RANGING, or HIGH-VOLATILITY. "
            "Useful for contextualising P&L moves."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

_TOOL_DISPATCH = {
    "get_positions":      lambda args, pd: _tool_get_positions(pd, **args),
    "get_pnl_summary":    lambda args, pd: _tool_get_pnl_summary(pd),
    "get_sector_exposure":lambda args, pd: _tool_get_sector_exposure(pd),
    "get_risk_score":     lambda args, pd: _tool_get_risk_score(pd),
    "get_tick_anomalies": lambda args, pd: _tool_get_tick_anomalies(**args),
    "get_market_regime":  lambda args, pd: _tool_get_market_regime(),
}


def _run_tool(name: str, input_args: dict, portfolio_data: dict) -> str:
    """Execute a tool call and return JSON-serialised result."""
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(input_args, portfolio_data)
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


SYSTEM_PROMPT = """\
You are a professional portfolio assistant for a multi-broker trading account
with positions at Zerodha Kite (Indian equities / F&O) and Interactive Brokers
(US equities).

You have access to live tools — always call them to get fresh data rather than
guessing. When answering questions involving numbers, call the relevant tool
first, then reply with the result.

Rules:
- Use ₹ for INR amounts, $ for USD. Round monetary values to 2 decimal places.
- If asked about risk, always call get_risk_score first.
- If asked about sector or allocation, call get_sector_exposure.
- Be concise and direct. Use markdown bullet points for lists.
- Never suggest placing orders — this is a read-only system.
"""


def ask(
    question: str,
    portfolio_data: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """
    Send a question to Claude with tool-use enabled.

    Returns (answer_text, updated_history) so multi-turn sessions work.
    history should be passed in from the previous turn for conversation memory.
    """
    if portfolio_data is None:
        portfolio_data = _load_portfolio()

    client   = _get_claude()
    messages = list(history or [])
    messages.append({"role": "user", "content": question})

    for _ in range(8):          # max 8 tool-call rounds
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = " ".join(
                b.text for b in response.content if hasattr(b, "text")
            ).strip()
            return text, messages

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_json = _run_tool(block.name, block.input, portfolio_data)
                    log.info("Tool call: %s → %s…", block.name, result_json[:80])
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result_json,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "(No response generated)", messages


def daily_brief(portfolio_data: dict | None = None) -> str:
    """Plain-English daily brief incorporating regime + risk score."""
    prompt = (
        "Generate a concise daily portfolio brief for a professional trader. "
        "Structure it as 6-8 bullet points covering:\n"
        "1. Total portfolio value and unrealised P&L in both ₹ and $\n"
        "2. Top gainer and top loser by symbol\n"
        "3. Sector with highest concentration\n"
        "4. Current market regime (from tick data)\n"
        "5. Portfolio risk score and what's driving it\n"
        "6. Any tick anomalies detected\n"
        "7. One concise actionable observation (read-only — no order suggestions)\n"
        "Be specific with numbers. Keep each bullet to 1-2 sentences."
    )
    answer, _ = ask(prompt, portfolio_data)
    return answer


def risk_report(portfolio_data: dict | None = None) -> str:
    """Detailed risk breakdown with Claude commentary."""
    prompt = (
        "Run a full portfolio risk assessment. Call get_risk_score and "
        "get_sector_exposure. Then write a 6-8 sentence risk report explaining: "
        "the overall risk score and label, what's driving concentration, "
        "which sector dominates, broker split, and one concrete way to reduce "
        "the top risk factor (without suggesting any orders)."
    )
    answer, _ = ask(prompt, portfolio_data)
    return answer


def detect_tick_anomalies(
    db_path: str       = str(DB_PATH),
    z_threshold: float = 2.5,
    lookback_rows: int = 100,
) -> pd.DataFrame:
    """
    Scan tick DB and flag symbols whose latest LTP deviates > z_threshold
    standard deviations from the rolling mean of the last `lookback_rows` ticks.
    """
    if not Path(db_path).exists():
        log.warning("Tick DB not found at %s — run kite/ticks.py first.", db_path)
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    df   = pd.read_sql_query(
        f"SELECT symbol, ltp, ts FROM ticks ORDER BY id DESC LIMIT {lookback_rows * 10}",
        conn,
    )
    conn.close()

    if df.empty:
        return pd.DataFrame()

    anomalies = []
    for symbol, group in df.groupby("symbol"):
        if len(group) < 5:
            continue
        mean_ltp = group["ltp"].mean()
        std_ltp  = group["ltp"].std()
        if std_ltp == 0:
            continue
        latest = group.iloc[0]["ltp"]
        z      = (latest - mean_ltp) / std_ltp
        if abs(z) >= z_threshold:
            anomalies.append({
                "symbol":     symbol,
                "latest_ltp": round(latest, 2),
                "mean_ltp":   round(mean_ltp, 2),
                "std_ltp":    round(std_ltp, 4),
                "z_score":    round(z, 3),
                "direction":  "SPIKE ▲" if z > 0 else "DIP ▼",
            })

    result = pd.DataFrame(anomalies)
    if not result.empty:
        result = result.sort_values("z_score", key=abs, ascending=False)
    return result


def explain_anomalies(anomalies: pd.DataFrame, portfolio_data: dict | None = None) -> str:
    """Ask Claude to explain detected anomalies in context of the portfolio."""
    if anomalies.empty:
        return "No tick anomalies detected."
    question = (
        f"I have detected these price anomalies in my live tick stream:\n"
        f"{anomalies.to_markdown(index=False)}\n\n"
        "First call get_positions to check whether I hold these symbols. "
        "Then briefly explain each anomaly (2-3 sentences each) and whether "
        "it warrants immediate attention given my positions."
    )
    answer, _ = ask(question, portfolio_data)
    return answer


def interactive_repl(portfolio_data: dict) -> None:
    """
    Interactive Q&A loop with conversation memory.
    Claude remembers previous exchanges within the session.
    """
    from rich.console  import Console
    from rich.markdown import Markdown

    console = Console()
    console.print(
        "\n[bold cyan]AI Portfolio Assistant[/bold cyan]  "
        "[dim](Claude · tool-use enabled · type 'exit' to quit)[/dim]\n"
    )
    console.print(
        "[dim]Try: 'What is my risk score?'  ·  'Which sector am I overweight in?'  ·  "
        "'Summarise yesterday\\'s anomalies'[/dim]\n"
    )

    history: list[dict] = []

    while True:
        try:
            question = input("You › ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if question.lower() in ("exit", "quit", "q"):
            break
        if not question:
            continue

        try:
            answer, history = ask(question, portfolio_data, history)
            console.print(Markdown(answer))
            console.print()
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Portfolio Assistant")
    parser.add_argument("--brief",   action="store_true", help="Daily P&L brief")
    parser.add_argument("--anomaly", action="store_true", help="Tick anomaly scan")
    parser.add_argument("--risk",    action="store_true", help="Portfolio risk report")
    parser.add_argument("--ask",     type=str,            help="One-shot question")
    args = parser.parse_args()

    portfolio_data = _load_portfolio()

    if args.brief:
        print("\n" + daily_brief(portfolio_data))

    elif args.anomaly:
        from rich.console import Console
        from rich.table   import Table
        console   = Console()
        anomalies = detect_tick_anomalies()
        if anomalies.empty:
            console.print("[green]No anomalies detected.[/green]")
        else:
            t = Table(title="Tick Anomalies", show_lines=True)
            for col in anomalies.columns:
                t.add_column(col, style="yellow")
            for _, row in anomalies.iterrows():
                t.add_row(*[str(v) for v in row])
            console.print(t)
            console.print("\n[bold]Claude's analysis:[/bold]")
            console.print(explain_anomalies(anomalies, portfolio_data))

    elif args.risk:
        print("\n" + risk_report(portfolio_data))

    elif args.ask:
        answer, _ = ask(args.ask, portfolio_data)
        print(f"\n{answer}")

    else:
        interactive_repl(portfolio_data)
