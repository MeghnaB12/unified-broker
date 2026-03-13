import sys
import time
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH, IBKR_CSV, USD_INR_FALLBACK

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

st.set_page_config(
    page_title="Unified Broker Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("⚙️ Settings")
    broker_filter = st.multiselect(
        "Broker",
        options=["Kite", "IBKR", "Both"],
        default=["Both"],
    )
    auto_refresh = st.checkbox("Auto-refresh (30 s)", value=False)
    st.divider()
    st.caption("Read-only. No orders placed.")


@st.cache_data(ttl=30, show_spinner=False)
def load_portfolio():
    """Load unified portfolio from both brokers."""
    from unified.portfolio import build_unified_portfolio, get_live_usd_inr

    usd_inr       = get_live_usd_inr()
    kite_holdings = pd.DataFrame()
    kite_net      = pd.DataFrame()
    ibkr_pos      = pd.DataFrame()
    kite_orders   = pd.DataFrame()

    try:
        from kite.auth      import get_kite_client
        from kite.portfolio import fetch_holdings, fetch_positions, fetch_orders
        kite          = get_kite_client()
        kite_holdings = fetch_holdings(kite)
        kite_net, _   = fetch_positions(kite)
        kite_orders   = fetch_orders(kite)
    except Exception as exc:
        st.sidebar.warning(f"Kite: {exc}")

    try:
        from ibkr.auth      import get_ibkr_client
        from ibkr.portfolio import fetch_positions as ibkr_fetch
        ib       = get_ibkr_client()
        ibkr_pos = ibkr_fetch(ib)
        ib.disconnect()
    except Exception as exc:
        st.sidebar.warning(f"IBKR: {exc}")

    unified = build_unified_portfolio(kite_holdings, kite_net, ibkr_pos, usd_inr)
    return unified, usd_inr, kite_orders


@st.cache_data(ttl=10, show_spinner=False)
def load_tick_data(symbol: str = None, limit: int = 200) -> pd.DataFrame:
    """Load recent ticks from SQLite."""
    db = Path(DB_PATH)
    if not db.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(str(db))
    where = f"WHERE symbol = '{symbol}'" if symbol else ""
    df = pd.read_sql_query(
        f"SELECT ts, symbol, ltp FROM ticks {where} ORDER BY id DESC LIMIT {limit}",
        conn,
    )
    conn.close()
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_ibkr_csv() -> pd.DataFrame:
    """Load IBKR mid-price CSV."""
    csv_file = Path(IBKR_CSV)
    if not csv_file.exists():
        return pd.DataFrame()
    df = pd.read_csv(csv_file, parse_dates=["timestamp"])
    return df


def run_ai_query(question: str, unified_df: pd.DataFrame, usd_inr: float) -> str:
    """Send question to the AI assistant and return the answer."""
    try:
        from ai.assistant import ask
        portfolio_data = {
            "unified_df":  unified_df,
            "usd_inr":     usd_inr,
            "kite_orders": pd.DataFrame(),
        }
        return ask(question, portfolio_data)
    except Exception as exc:
        return f"⚠️ AI unavailable: {exc}"


st.title("📊 Unified Broker Dashboard")
st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

with st.spinner("Fetching live portfolio data…"):
    unified_df, usd_inr, kite_orders = load_portfolio()

col1, col2, col3, col4 = st.columns(4)

total_inr     = unified_df["market_value_inr"].sum()     if not unified_df.empty else 0
total_usd     = unified_df["market_value_usd"].sum()     if not unified_df.empty else 0
total_pnl_inr = unified_df["unrealised_pnl_inr"].sum()  if not unified_df.empty else 0
total_pnl_usd = unified_df["unrealised_pnl_usd"].sum()  if not unified_df.empty else 0
n_positions   = len(unified_df) if not unified_df.empty else 0

col1.metric("Total Value (INR)",    f"₹{total_inr:,.0f}",  delta=None)
col2.metric("Total Value (USD)",    f"${total_usd:,.0f}",  delta=None)
col3.metric("Unrealised P&L (INR)", f"₹{total_pnl_inr:,.0f}",
            delta=f"₹{total_pnl_inr:,.0f}", delta_color="normal")
col4.metric("Open Positions",       n_positions)

st.divider()

st.subheader("Holdings")

if unified_df.empty:
    st.info("No positions found. Check broker connections in the sidebar.")
else:
    display_df = unified_df.copy()

    selected = broker_filter if broker_filter != ["Both"] else ["Kite", "IBKR"]
    if "Both" not in broker_filter:
        display_df = display_df[display_df["broker"].isin(broker_filter)]

    def _color_pnl(val):
        try:
            f = float(val)
            if f > 0:  return "color: green"
            if f < 0:  return "color: red"
        except Exception:
            pass
        return ""

    styled = (
        display_df.style
        .format({
            "avg_cost":           "{:,.4f}",
            "ltp":                "{:,.4f}",
            "market_value_inr":   "₹{:,.2f}",
            "market_value_usd":   "${:,.2f}",
            "unrealised_pnl_inr": "₹{:,.2f}",
            "unrealised_pnl_usd": "${:,.2f}",
        }, na_rep="—")
        .applymap(_color_pnl, subset=["unrealised_pnl_inr", "unrealised_pnl_usd"])
    )
    st.dataframe(styled, use_container_width=True, height=300)

    st.subheader("Allocation by Broker")
    pie_data = display_df.groupby("broker")["market_value_inr"].sum().reset_index()
    fig_pie  = px.pie(
        pie_data,
        names="broker",
        values="market_value_inr",
        title="Portfolio Allocation (INR)",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

st.subheader("Live Tick Stream (Kite)")

tick_symbols = ["ITC", "ONGC", "NIFTY 50"]
selected_sym = st.selectbox("Symbol", tick_symbols, index=0)
tick_df      = load_tick_data(symbol=selected_sym)

if tick_df.empty:
    st.info(
        f"No tick data for {selected_sym}. "
        "Run `python kite/ticks.py` to start the tick stream."
    )
else:
    fig_tick = go.Figure()
    fig_tick.add_trace(go.Scatter(
        x=tick_df["ts"],
        y=tick_df["ltp"],
        mode="lines+markers",
        name=selected_sym,
        line=dict(color="#00b4d8", width=1.5),
        marker=dict(size=3),
    ))
    fig_tick.update_layout(
        title=f"{selected_sym} — LTP over time",
        xaxis_title="Time (UTC)",
        yaxis_title="LTP (₹)",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig_tick, use_container_width=True)

st.divider()

st.subheader("IBKR Mid-Price Feed")

ibkr_df = load_ibkr_csv()

if ibkr_df.empty:
    st.info(
        "No IBKR mid-price data. "
        "Run `python ibkr/market_data.py` to start the feed."
    )
else:
    ibkr_symbols = ibkr_df["symbol"].unique().tolist()
    ibkr_sym     = st.selectbox("IBKR Symbol", ibkr_symbols)
    sub_df       = ibkr_df[ibkr_df["symbol"] == ibkr_sym].dropna(subset=["mid_price"])

    fig_ibkr = go.Figure()
    fig_ibkr.add_trace(go.Scatter(
        x=sub_df["timestamp"],
        y=sub_df["mid_price"],
        mode="lines+markers",
        name=ibkr_sym,
        line=dict(color="#48cae4", width=1.5),
        marker=dict(size=3),
    ))
    fig_ibkr.update_layout(
        title=f"{ibkr_sym} — Mid-price (USD)",
        xaxis_title="Time (UTC)",
        yaxis_title="Mid-price ($)",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig_ibkr, use_container_width=True)

st.divider()

if not kite_orders.empty:
    with st.expander("Kite Order Book"):
        st.dataframe(kite_orders, use_container_width=True)

st.subheader("🤖 AI Portfolio Assistant")
st.caption("Ask anything about your portfolio in plain English.")

ai_presets = [
    "What is my total unrealised P&L in USD today?",
    "Which broker holds the most equity by value?",
    "List all positions with a loss greater than ₹5,000.",
    "Give me a daily portfolio brief.",
    "What percentage of my portfolio is in US equities?",
]

preset_q = st.selectbox("Quick questions", ["(type your own…)"] + ai_presets)
user_q   = st.text_input(
    "Your question",
    value="" if preset_q == "(type your own…)" else preset_q,
    placeholder="e.g. What is my biggest winner today?",
)

if st.button("Ask Claude", type="primary") and user_q.strip():
    with st.spinner("Thinking…"):
        answer = run_ai_query(user_q.strip(), unified_df, usd_inr)
    st.markdown(f"**Answer:**\n\n{answer}")

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
