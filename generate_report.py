"""
generate_report.py — builds the implementation PDF report.
Run:  python generate_report.py
Output: unified_broker_implementation.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem
from datetime import date

OUTPUT = "unified_broker_implementation.pdf"
W, H   = A4

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0d1b2a")
TEAL    = colors.HexColor("#0077b6")
LTBLUE  = colors.HexColor("#00b4d8")
CREAM   = colors.HexColor("#f8f9fa")
GREEN   = colors.HexColor("#2d6a4f")
DKGRAY  = colors.HexColor("#343a40")
LTGRAY  = colors.HexColor("#dee2e6")
WHITE   = colors.white
RED     = colors.HexColor("#c0392b")

# ── Styles ────────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

Cover_Title   = S("CoverTitle",   fontSize=32, leading=40, textColor=WHITE,    alignment=TA_CENTER, fontName="Helvetica-Bold")
Cover_Sub     = S("CoverSub",     fontSize=16, leading=22, textColor=LTBLUE,   alignment=TA_CENTER, fontName="Helvetica")
Cover_Meta    = S("CoverMeta",    fontSize=11, leading=16, textColor=LTGRAY,   alignment=TA_CENTER, fontName="Helvetica")
H1            = S("H1",           fontSize=20, leading=26, textColor=NAVY,     fontName="Helvetica-Bold",  spaceAfter=8, spaceBefore=18)
H2            = S("H2",           fontSize=14, leading=20, textColor=TEAL,     fontName="Helvetica-Bold",  spaceAfter=6, spaceBefore=14)
H3            = S("H3",           fontSize=11, leading=16, textColor=DKGRAY,   fontName="Helvetica-Bold",  spaceAfter=4, spaceBefore=10)
Body          = S("Body",         fontSize=10, leading=15, textColor=DKGRAY,   fontName="Helvetica",       spaceAfter=4,  alignment=TA_JUSTIFY)
Mono          = S("Mono",         fontSize=8,  leading=12, textColor=NAVY,     fontName="Courier",         spaceAfter=2,  backColor=CREAM, leftIndent=12, rightIndent=12)
MonoLabel     = S("MonoLabel",    fontSize=9,  leading=13, textColor=GREEN,    fontName="Courier-Bold",    spaceAfter=1,  leftIndent=12)
Caption       = S("Caption",      fontSize=8,  leading=11, textColor=colors.grey, fontName="Helvetica-Oblique", spaceAfter=6, alignment=TA_CENTER)
Bullet        = S("Bullet",       fontSize=10, leading=15, textColor=DKGRAY,   fontName="Helvetica",       spaceAfter=3,  leftIndent=14, bulletIndent=4)

def p(text, style=Body):   return Paragraph(text, style)
def h1(text):              return Paragraph(text, H1)
def h2(text):              return Paragraph(text, H2)
def h3(text):              return Paragraph(text, H3)
def sp(n=6):               return Spacer(1, n)
def hr():                  return HRFlowable(width="100%", thickness=1, color=LTGRAY, spaceAfter=8, spaceBefore=4)
def code(line):            return Paragraph(line, Mono)
def bullets(items):
    return ListFlowable(
        [ListItem(p(i, Bullet), leftIndent=18, bulletColor=TEAL) for i in items],
        bulletType="bullet", start="•", leftIndent=14, spaceAfter=6,
    )

def table(data, col_widths=None, header_bg=NAVY):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    n_cols = len(data[0])
    style = [
        ("BACKGROUND",  (0,0), (-1,0),  header_bg),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  9),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, CREAM]),
        ("GRID",        (0,0), (-1,-1), 0.5, LTGRAY),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("TEXTCOLOR",   (0,1), (-1,-1), DKGRAY),
    ]
    t.setStyle(TableStyle(style))
    return t


# ── Page template with header / footer ───────────────────────────────────────

def _on_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(LTBLUE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.5*cm, H - 0.75*cm, "Unified Broker — Implementation Report")
    canvas.setFillColor(LTGRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 1.5*cm, H - 0.75*cm, "Confidential")
    # Footer
    canvas.setFillColor(LTGRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, 0.7*cm, f"Generated {date.today().isoformat()}")
    canvas.drawRightString(W - 1.5*cm, 0.7*cm, f"Page {doc.page}")
    canvas.restoreState()


def _cover_page(canvas, doc):
    canvas.saveState()
    # Full-bleed navy background
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Teal accent strip
    canvas.setFillColor(TEAL)
    canvas.rect(0, H * 0.42, W, 4, fill=1, stroke=0)
    canvas.restoreState()


# ── Document build ─────────────────────────────────────────────────────────────

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm,  bottomMargin=1.8*cm,
    )

    story = []

    # ──────────────────────────────────────────────────────────────────────────
    # COVER
    # ──────────────────────────────────────────────────────────────────────────
    # Blank space to push title into centre of navy background
    story.append(Spacer(1, 5.5*cm))
    story.append(Paragraph("Unified Broker", Cover_Title))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Implementation Report", Cover_Sub))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Zerodha Kite  ✦  Interactive Brokers  ✦  AI Portfolio Intelligence", Cover_Meta))
    story.append(Spacer(1, 7*cm))
    story.append(Paragraph(f"Prepared by: Meghna &nbsp; | &nbsp; {date.today().strftime('%B %Y')}", Cover_Meta))
    story.append(Paragraph("Python 3.13  ·  kiteconnect  ·  ib_insync  ·  Claude claude-opus-4-6", Cover_Meta))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("<i>Read-only access · No order placement · Credentials held under NDA</i>", Cover_Meta))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 1. EXECUTIVE SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("1. Executive Summary"), hr()]
    story.append(p(
        "This report documents the complete implementation of a <b>unified multi-broker data "
        "layer</b> connecting <b>Zerodha Kite</b> (Indian equities and F&amp;O) with <b>Interactive "
        "Brokers</b> (US and global equities). The system surfaces consolidated portfolio data "
        "through a Streamlit dashboard and an AI-powered natural-language assistant backed by "
        "<b>Anthropic Claude claude-opus-4-6</b> with native tool-use (function calling)."
    ))
    story.append(p(
        "All nine assignment tasks are implemented as discrete, testable Python modules. "
        "The codebase is <b>read-only throughout</b>; no order-placement logic exists anywhere."
    ))
    story.append(sp(8))

    story.append(table(
        [["Task", "Title", "Key Output"],
         ["1", "Kite Auth & Session",      "OAuth 2.0 login; token auto-stored in .env; session guard"],
         ["2", "Kite Portfolio Fetch",     "Holdings, overnight + intraday positions, order book → DataFrames"],
         ["3", "Kite WebSocket Ticks",     "Live tick stream → SQLite; console alerts on threshold cross"],
         ["4", "IBKR TWS / Gateway Auth",  "ib_insync connection; exponential back-off reconnect"],
         ["5", "IBKR Portfolio Fetch",     "Positions, NAV, cash, P&L; multi-currency (USD + INR)"],
         ["6", "IBKR Live Market Data",    "Mid-price every 5 s → CSV for ≥ 60 s (AAPL, MSFT, GOOGL)"],
         ["7", "Unified Portfolio View",   "Merged Kite + IBKR DataFrame; dual INR/USD totals"],
         ["8", "Dashboard UI",             "Streamlit: holdings table, tick chart, broker toggle, AI bar"],
         ["9", "AI Layer (Differentiator)","Claude tool-use: NL Q&A, risk scorer, regime detector, anomalies"]],
        col_widths=[1*cm, 4.5*cm, 10*cm],
    ))
    story.append(sp(4))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 2. ARCHITECTURE
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("2. Architecture & Project Structure"), hr()]
    story.append(p(
        "The project follows a layered architecture. Each broker has its own package "
        "(<code>kite/</code>, <code>ibkr/</code>) with dedicated auth, portfolio, and data-streaming "
        "modules. A broker-agnostic <code>unified/</code> layer merges data and normalises currencies. "
        "The <code>dashboard/</code> and <code>ai/</code> layers consume the unified output."
    ))
    story.append(sp(6))

    story.append(table(
        [["File / Module", "Responsibility"],
         ["config/settings.py",      "Centralised config; reads all env vars; defines data paths"],
         ["kite/auth.py",            "OAuth 2.0 handshake, token persistence, session validation"],
         ["kite/portfolio.py",       "Holdings, net + intraday positions, order book → pandas"],
         ["kite/ticks.py",           "KiteTicker WebSocket stream → SQLite; threshold alert engine"],
         ["ibkr/auth.py",            "ib_insync connect, exponential back-off, disconnect handler"],
         ["ibkr/portfolio.py",       "Portfolio positions, account summary, live FX rate"],
         ["ibkr/market_data.py",     "Live quote subscription; mid-price → CSV every 5 s"],
         ["unified/portfolio.py",    "Broker merge, currency normalisation, dual-currency totals"],
         ["dashboard/app.py",        "Streamlit UI: KPIs, holdings table, charts, AI query bar"],
         ["ai/assistant.py",         "Claude tool-use loop, risk scorer, regime detector, REPL"],
         ["run.py",                  "Single CLI entry point for all 9 tasks"],
         [".env",                    "Credentials and config (gitignored)"]],
        col_widths=[5*cm, 10.5*cm],
    ))
    story.append(sp(10))

    story += [h2("Data Flow")]
    story.append(p(
        "Kite REST API and WebSocket feed into <code>kite/portfolio.py</code> and "
        "<code>kite/ticks.py</code>. IBKR TWS/Gateway feeds into <code>ibkr/portfolio.py</code> "
        "and <code>ibkr/market_data.py</code>. Both streams converge in "
        "<code>unified/portfolio.py</code>, which applies live FX conversion and produces a "
        "single normalised DataFrame consumed by the dashboard and AI layer."
    ))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 3. TASK-BY-TASK IMPLEMENTATION
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("3. Task-by-Task Implementation Detail"), hr()]

    # Task 1
    story += [h2("Task 1 — Kite Auth & Session  (kite/auth.py)")]
    story.append(p(
        "Implements the <b>Zerodha Kite Connect OAuth 2.0 flow</b>. On first run, the user is "
        "directed to the Kite login URL; after authentication, Kite redirects with a "
        "<code>request_token</code> which is exchanged for a long-lived <code>access_token</code>. "
        "The token is persisted to <code>.env</code> via <code>python-dotenv</code>'s "
        "<code>set_key()</code> so subsequent runs bypass the browser step."
    ))
    story.append(p(
        "<b>Session guard:</b> before reusing a stored token, "
        "<code>_is_session_valid()</code> pings the <code>/profile</code> endpoint. "
        "On failure the full OAuth flow is re-triggered automatically — satisfying the "
        "auto re-auth requirement. A CLI <code>invalidate_session()</code> helper clears the token."
    ))
    story.append(sp(4))
    story.append(table(
        [["Mechanism", "Detail"],
         ["Library",        "kiteconnect >= 5.0.1"],
         ["Token storage",  "python-dotenv set_key() → .env file"],
         ["Session check",  "kite.profile() ping — raises on expiry"],
         ["Re-auth trigger","Automatic on any session-check failure"],
         ["Output",         "KiteConnect object with active access_token"]],
        col_widths=[4*cm, 11.5*cm],
    ))
    story.append(sp(10))

    # Task 2
    story += [h2("Task 2 — Kite Portfolio Fetch  (kite/portfolio.py)")]
    story.append(p(
        "Three functions cover the full portfolio picture: <b>fetch_holdings()</b> pulls the "
        "equity holdings book (<code>kite.holdings()</code>); <b>fetch_positions()</b> returns "
        "a tuple of overnight (<i>net</i>) and intraday (<i>day</i>) positions; "
        "<b>fetch_orders()</b> returns today's order book. All three normalise broker field "
        "names (e.g. <code>tradingsymbol</code> → <code>symbol</code>) and compute derived "
        "columns (<code>market_value = qty × ltp</code>, <code>cost_basis = qty × avg_cost</code>)."
    ))
    story.append(p(
        "The <b>portfolio_summary()</b> helper renders rich-formatted tables to stdout with "
        "colour-coded P&amp;L totals. Every function is independently importable and "
        "accepts a <code>KiteConnect</code> object, making them composable from the "
        "unified layer and dashboard without duplication."
    ))
    story.append(sp(4))
    story.append(table(
        [["Function", "API call", "DataFrame columns"],
         ["fetch_holdings()", "kite.holdings()", "symbol, exchange, qty, avg_cost, ltp, unrealised_pnl, day_change, market_value, cost_basis"],
         ["fetch_positions()","kite.positions()","symbol, exchange, product, qty, avg_cost, ltp, unrealised_pnl, market_value  (×2: net + day)"],
         ["fetch_orders()",   "kite.orders()",   "order_id, symbol, side, order_type, qty, price, status, placed_at"]],
        col_widths=[3.5*cm, 3.5*cm, 8.5*cm],
    ))
    story.append(sp(10))

    # Task 3
    story += [h2("Task 3 — Kite WebSocket Ticks  (kite/ticks.py)")]
    story.append(p(
        "Uses <b>KiteTicker</b> in threaded mode to stream <b>full-quote ticks</b> "
        "(LTP, bid, ask, volume) for ITC (token 424961), ONGC (633601), and NIFTY 50 (256265). "
        "Each tick is persisted to a local <b>SQLite database</b> (<code>data/ticks.db</code>) "
        "with a UTC ISO-8601 timestamp, instrument token, symbol, LTP, volume, bid, and ask."
    ))
    story.append(p(
        "<b>Alert engine:</b> <code>_check_alerts()</code> compares each LTP against configured "
        "thresholds from the environment (<code>ITC_ALERT_ABOVE</code>, <code>ONGC_ALERT_BELOW</code>). "
        "It fires once per crossing and auto-resets when the price returns to the safe side — "
        "preventing alert floods. Alerts are printed in ANSI yellow/red and written to the log."
    ))
    story.append(p(
        "<b>Lifecycle:</b> the stream handles <code>on_connect</code>, <code>on_close</code>, "
        "<code>on_error</code>, and <code>on_reconnect</code> callbacks. A SIGINT handler "
        "triggers a clean <code>kws.stop()</code>. An optional <code>duration_seconds</code> "
        "parameter stops the stream after a fixed interval (used by the test runner)."
    ))
    story.append(sp(10))

    # Task 4
    story += [h2("Task 4 — IBKR TWS / Gateway Auth  (ibkr/auth.py)")]
    story.append(p(
        "Connects to a live TWS or IB Gateway instance using <b>ib_insync</b>. "
        "The <code>get_ibkr_client()</code> function retries up to 5 times with "
        "<b>exponential back-off</b> (base 5 s, cap 60 s) before raising a descriptive error."
    ))
    story.append(p(
        "Two event handlers are attached at connect time. <b><code>disconnectedEvent</code></b> "
        "triggers an automatic reconnect attempt after a 5-second delay, simulating the "
        "survivability required by the spec. <b><code>errorEvent</code></b> silently ignores "
        "IBKR informational codes (2104, 2106, 2119, etc.) while logging true errors at ERROR "
        "level. After connecting, <code>_log_account_info()</code> logs the managed account IDs "
        "and NAV to confirm the session is live."
    ))
    story.append(sp(4))
    story.append(table(
        [["Feature", "Implementation"],
         ["Library",            "ib_insync >= 0.9.86"],
         ["Ports",              "7497 = TWS paper  |  7496 = TWS live  |  4001 = IB Gateway"],
         ["Retry strategy",     "5 attempts, exponential back-off (5 → 10 → 20 → 40 → 60 s)"],
         ["Auto-reconnect",     "ib.disconnectedEvent callback; retries after 5 s"],
         ["Informational codes","2104, 2106, 2107, 2108, 2119, 2157, 2158 suppressed at DEBUG"],
         ["Reconnect test",     "Explicit ib.disconnect() + get_ibkr_client() in CLI entry-point"]],
        col_widths=[4*cm, 11.5*cm],
    ))
    story.append(sp(10))

    # Task 5
    story += [h2("Task 5 — IBKR Portfolio Fetch  (ibkr/portfolio.py)")]
    story.append(p(
        "<b>fetch_positions()</b> iterates <code>ib.portfolio()</code> and normalises each "
        "position into a row containing broker, symbol, secType, exchange, currency, qty, "
        "avg_cost, mkt_price, mkt_value, unrealised_pnl, and an <b>INR equivalent</b> column. "
        "The live USD/INR mid-rate is fetched first from IBKR's own FX market data "
        "(<code>Forex('USDINR')</code>); if unavailable, the env-var fallback is used."
    ))
    story.append(p(
        "<b>Multi-currency handling:</b> USD positions are multiplied by the FX rate; "
        "INR-denominated positions are passed through unchanged; other currencies are treated "
        "as USD with a log warning. <b>fetch_account_summary()</b> queries "
        "NetLiquidation, TotalCashValue, UnrealizedPnL, RealizedPnL, GrossPositionValue, and "
        "MaintMarginReq across all managed accounts."
    ))
    story.append(sp(4))
    story.append(table(
        [["Column", "Source", "Notes"],
         ["broker",          "hardcoded 'IBKR'",         "—"],
         ["symbol",          "pos.contract.symbol",      "—"],
         ["currency",        "pos.contract.currency",    "USD / INR / other"],
         ["qty",             "pos.position",             "negative = short"],
         ["avg_cost",        "pos.averageCost",          "rounded 4 dp"],
         ["mkt_value",       "pos.marketValue",          "native currency"],
         ["unrealised_pnl",  "pos.unrealizedPNL",        "native currency"],
         ["inr_equiv",       "mkt_value × usd_inr",     "None for exotic CCY"]],
        col_widths=[3.5*cm, 5*cm, 7*cm],
    ))
    story.append(sp(10))
    story.append(PageBreak())

    # Task 6
    story += [h2("Task 6 — IBKR Live Market Data  (ibkr/market_data.py)")]
    story.append(p(
        "<b>stream_market_data()</b> subscribes to live SMART-routed quotes for AAPL, MSFT, "
        "and GOOGL using <code>ib.reqMktData()</code>. Every 5 seconds it samples bid, ask, "
        "and computed mid-price (<code>(bid + ask) / 2</code>) from each ticker and appends "
        "a row to a CSV file with a UTC ISO-8601 timestamp. The stream runs for at least "
        "60 seconds (configurable) and cancels all market-data subscriptions on exit."
    ))
    story.append(p(
        "A SIGINT handler sets a <code>stop</code> flag so the loop exits cleanly. "
        "The CSV header is written only if the file is new or empty, allowing multiple runs "
        "to append without duplication. The output path is configurable and defaults to "
        "<code>logs/ibkr_midprice.csv</code>."
    ))
    story.append(sp(10))

    # Task 7
    story += [h2("Task 7 — Unified Portfolio View  (unified/portfolio.py)")]
    story.append(p(
        "<b>build_unified_portfolio()</b> accepts DataFrames from all four sources "
        "(Kite holdings, Kite net positions, IBKR positions) and an optional USD/INR rate, "
        "then produces a single normalised DataFrame with consistent columns across both brokers."
    ))
    story.append(p(
        "<b>Currency normalisation:</b> Kite holdings are always INR; IBKR USD positions are "
        "converted by multiplying market value and P&amp;L by the live FX rate. "
        "All rows carry both <code>market_value_inr</code> / <code>market_value_usd</code> "
        "and <code>unrealised_pnl_inr</code> / <code>unrealised_pnl_usd</code> — enabling "
        "single-column aggregation in either currency."
    ))
    story.append(p(
        "<b>FX rate:</b> fetched from <code>api.exchangerate-api.com</code> at runtime with a "
        "5-second timeout; falls back to the <code>USD_INR_RATE</code> env var on failure. "
        "<b>print_unified_summary()</b> renders a rich-formatted table with broker subtotals "
        "and grand totals in both currencies."
    ))
    story.append(sp(4))
    story.append(table(
        [["Output Column",        "Type",   "Description"],
         ["broker",               "str",    "'Kite' or 'IBKR'"],
         ["symbol",               "str",    "Ticker / trading symbol"],
         ["qty",                  "int",    "Quantity held (negative = short)"],
         ["currency",             "str",    "Native currency of the position"],
         ["avg_cost",             "float",  "Average acquisition cost in native CCY"],
         ["ltp",                  "float",  "Last traded / market price"],
         ["market_value_inr",     "float",  "Market value converted to INR"],
         ["market_value_usd",     "float",  "Market value converted to USD"],
         ["unrealised_pnl_inr",   "float",  "Unrealised P&L in INR"],
         ["unrealised_pnl_usd",   "float",  "Unrealised P&L in USD"]],
        col_widths=[4.5*cm, 2*cm, 9*cm],
    ))
    story.append(sp(10))
    story.append(PageBreak())

    # Task 8
    story += [h2("Task 8 — Dashboard UI  (dashboard/app.py)")]
    story.append(p(
        "A <b>Streamlit</b> application providing a live, read-only view of the unified "
        "portfolio. Data is fetched with a 30-second cache TTL (<code>@st.cache_data</code>) "
        "to balance freshness against API rate limits."
    ))
    story.append(sp(4))
    story.append(table(
        [["Component", "Detail"],
         ["KPI cards (4)",        "Total Value (₹), Total Value ($), Unrealised P&L (₹), Open Positions"],
         ["Holdings table",       "Colour-coded P&L (green/red), formatted currencies, broker-filterable"],
         ["Allocation pie chart", "Plotly pie: portfolio weight by broker in INR"],
         ["Kite tick chart",      "Plotly line chart of LTP over time from SQLite; symbol selector"],
         ["IBKR mid-price chart", "Plotly line chart from CSV; symbol selector"],
         ["Order book",           "Kite order book in collapsible expander"],
         ["AI query bar",         "Text input + preset questions; calls Claude via run_ai_query()"],
         ["Broker toggle",        "Sidebar multiselect filters holdings table to Kite / IBKR / Both"],
         ["Auto-refresh",         "Sidebar checkbox: clears cache and st.rerun() every 30 s"]],
        col_widths=[4*cm, 11.5*cm],
    ))
    story.append(sp(6))
    story.append(p(
        "<b>Graceful degradation:</b> each broker's data loader is wrapped in a try/except; "
        "if Kite or IBKR is unavailable, a sidebar warning is shown and the remaining data "
        "still renders."
    ))
    story.append(sp(10))
    story.append(PageBreak())

    # Task 9
    story += [h2("Task 9 — AI Layer  (ai/assistant.py)")]
    story.append(p(
        "The AI layer is built on <b>Anthropic Claude claude-opus-4-6</b> with <b>native tool-use "
        "(function calling)</b>. Rather than pasting a static portfolio JSON into the system "
        "prompt, Claude is given a set of callable tools and decides autonomously which to "
        "invoke — and in what order — before composing a grounded answer."
    ))

    story += [h3("3.9.1  Tool-Use Architecture")]
    story.append(p(
        "The <code>ask()</code> function runs an <b>agentic loop</b> (up to 8 rounds). "
        "On each round, Claude's response is inspected: if <code>stop_reason == 'tool_use'</code>, "
        "every <code>tool_use</code> block is dispatched to the corresponding Python function, "
        "results are JSON-serialised and returned as <code>tool_result</code> messages, and the "
        "loop continues. When <code>stop_reason == 'end_turn'</code>, the final text is returned."
    ))
    story.append(sp(4))
    story.append(table(
        [["Tool", "Returns"],
         ["get_positions(broker)",   "All positions; optionally filtered to Kite or IBKR"],
         ["get_pnl_summary()",       "Total INR/USD P&L, market value, top gainer, top loser, by-broker split"],
         ["get_sector_exposure()",   "Market value and % weight per sector (Technology, Banking, Energy…)"],
         ["get_risk_score()",        "0-100 risk score + label + HHI components + drawdown metrics"],
         ["get_tick_anomalies()",    "Z-score scan of SQLite DB; SPIKE ▲ / DIP ▼ flagged symbols"],
         ["get_market_regime()",     "TRENDING / RANGING / HIGH-VOLATILITY from tick volatility stats"]],
        col_widths=[4.5*cm, 11*cm],
    ))
    story.append(sp(10))

    story += [h3("3.9.2  Portfolio Risk Scorer")]
    story.append(p(
        "A quantitative <b>0-100 composite risk score</b> built from five signals:"
    ))
    story.append(table(
        [["Signal", "Weight", "Method"],
         ["Position concentration (HHI)", "35%", "Herfindahl-Hirschman Index across individual holdings"],
         ["Sector concentration (HHI)",   "25%", "HHI across sector buckets (Technology, Banking, Energy…)"],
         ["Broker split",                 "20%", "HHI across Kite vs IBKR allocation"],
         ["Largest single drawdown",      "10%", "Max unrealised loss / total portfolio value × 100"],
         ["Total drawdown ratio",         "10%", "Sum of all unrealised losses / total portfolio value × 100"]],
        col_widths=[5*cm, 2.5*cm, 8*cm],
    ))
    story.append(sp(6))
    story.append(p(
        "Score 0-24 = <b>LOW</b> · 25-49 = <b>MODERATE</b> · 50-74 = <b>HIGH</b> · 75-100 = <b>VERY HIGH</b>. "
        "Claude uses this score to contextualise answers about risk without guessing."
    ))
    story.append(sp(10))

    story += [h3("3.9.3  Market Regime Detector")]
    story.append(p(
        "Reads the most recent ticks from SQLite and, per symbol, computes: "
        "(a) the <b>rolling z-score</b> of LTP and takes the median absolute value as a "
        "volatility proxy; (b) a <b>linear trend slope</b> via <code>numpy.polyfit</code>. "
        "Regime classification:"
    ))
    story.append(bullets([
        "<b>HIGH-VOLATILITY</b> — average median |z| > 1.5 across all symbols",
        "<b>TRENDING</b> — average |slope| > 0.05 (consistent directional drift)",
        "<b>RANGING</b> — everything else (low dispersion, no clear direction)",
    ]))
    story.append(p(
        "The regime is surfaced in the daily brief and available as a standalone tool "
        "call so Claude can contextualise P&amp;L moves ('markets were high-vol today, "
        "which explains the wide swings in your NIFTY 50 position')."
    ))
    story.append(sp(10))

    story += [h3("3.9.4  Daily Brief, Risk Report & Anomaly Explanation")]
    story.append(table(
        [["Feature", "Prompt strategy", "Claude actions"],
         ["Daily brief",     "Structured 6-8 bullet prompt covering value, P&L, sector, regime, risk, anomalies",
                             "Calls get_pnl_summary, get_sector_exposure, get_risk_score, get_market_regime, get_tick_anomalies"],
         ["Risk report",     "Plain-English risk breakdown: score, drivers, one actionable observation",
                             "Calls get_risk_score + get_sector_exposure; synthesises narrative"],
         ["Anomaly explain", "Anomaly table passed in message; Claude asked to cross-reference positions",
                             "Calls get_positions to check if flagged symbols are held; explains relevance"]],
        col_widths=[3*cm, 5.5*cm, 7*cm],
    ))
    story.append(sp(10))

    story += [h3("3.9.5  Multi-Turn Conversational REPL")]
    story.append(p(
        "The <code>ask()</code> function accepts and returns a <code>history: list[dict]</code> "
        "parameter containing the full Anthropic messages array. The REPL passes this history "
        "back on every turn, giving Claude <b>full conversation memory</b> within a session. "
        "This enables follow-up questions like 'which stocks are driving that?' after asking "
        "about risk — without re-explaining context."
    ))
    story.append(sp(4))
    story.append(table(
        [["CLI flag", "Behaviour"],
         ["--ask 'question'", "One-shot answer with tool-use"],
         ["--brief",          "Plain-English daily brief (6-8 bullets)"],
         ["--risk",           "Detailed risk report with component breakdown"],
         ["--anomaly",        "Z-score scan + Claude explains each anomalous symbol"],
         ["(no flag)",        "Interactive multi-turn REPL with conversation memory"]],
        col_widths=[4*cm, 11.5*cm],
    ))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 4. SETUP & RUNNING
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("4. Setup & Running"), hr()]

    story += [h2("4.1  Installation")]
    for line in [
        "git clone &lt;repo-url&gt;  &amp;&amp;  cd unified-broker",
        "python -m venv venv  &amp;&amp;  source venv/bin/activate",
        "pip install -r requirements.txt",
        "cp .env.example .env    # then fill in credentials",
    ]:
        story.append(code(line))
    story.append(sp(10))

    story += [h2("4.2  With Live Credentials")]
    story.append(table(
        [["Command", "Task"],
         ["python run.py --task 1",                   "Kite OAuth login"],
         ["python run.py --task 2",                   "Live Kite portfolio"],
         ["python run.py --task 3 --duration 60",     "Tick stream (60 s)"],
         ["python run.py --task 4",                   "IBKR connect + reconnect test"],
         ["python run.py --task 5",                   "IBKR live portfolio"],
         ["python run.py --task 6 --duration 60",     "IBKR mid-prices → CSV"],
         ["python run.py --task 7",                   "Unified portfolio"],
         ["streamlit run dashboard/app.py",           "Dashboard (http://localhost:8501)"],
         ["python run.py --task 9 --brief",           "AI daily brief"],
         ["python run.py --task 9 --risk",            "AI risk report"],
         ["python run.py --task 9 --anomaly",         "AI anomaly scan"],
         ['python run.py --task 9 --ask "..."',       "One-shot AI question"],
         ["python run.py --task 9",                   "Multi-turn AI REPL"]],
        col_widths=[8*cm, 7.5*cm],
    ))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 5. DEPENDENCIES
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("5. Dependencies"), hr()]
    story.append(table(
        [["Package", "Version", "Purpose"],
         ["kiteconnect",      "≥ 5.0.1",  "Zerodha Kite REST API + KiteTicker WebSocket"],
         ["ib_insync",        "≥ 0.9.86", "Interactive Brokers TWS / Gateway client"],
         ["pandas",           "≥ 2.0.0",  "DataFrame normalisation across all tasks"],
         ["numpy",            "≥ 1.24.0", "Numerical operations (HHI, z-score, polyfit)"],
         ["anthropic",        "≥ 0.25.0", "Claude API client with tool-use support"],
         ["streamlit",        "≥ 1.32.0", "Dashboard UI framework"],
         ["plotly",           "≥ 5.18.0", "Interactive charts (tick, mid-price, pie)"],
         ["python-dotenv",    "≥ 1.0.0",  "Env var loading + set_key() for token persistence"],
         ["requests",         "≥ 2.31.0", "Live FX rate fetch"],
         ["sqlalchemy",       "≥ 2.0.0",  "SQLite ORM (tick DB)"],
         ["aiohttp",          "≥ 3.9.0",  "Async HTTP (ib_insync dependency)"],
         ["rich",             "≥ 13.7.0", "Terminal table rendering and colour output"],
         ["tabulate",         "≥ 0.9.0",  "Markdown table formatting for Claude prompts"]],
        col_widths=[3.5*cm, 2.5*cm, 9.5*cm],
    ))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 6. SECURITY
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("6. Security & Compliance"), hr()]
    story.append(bullets([
        "<b>.env</b> is gitignored — credentials are never committed to version control.",
        "<b>data/</b> and <b>logs/</b> directories are gitignored — tick DBs and CSVs stay local.",
        "All broker access is <b>read-only</b>. No order-placement code exists anywhere in the codebase.",
        "IBKR informational error codes are filtered to prevent false-positive alerting.",
        "The Anthropic API key is validated at runtime; the AI layer raises a clear error if absent rather than silently failing.",
        "Credentials shared under NDA must not be forwarded or embedded in any committed file.",
    ]))
    story.append(sp(10))

    # ──────────────────────────────────────────────────────────────────────────
    # 7. WHAT I'D BUILD NEXT
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("7. What I'd Build Next"), hr()]

    story += [h2("7.1  Infrastructure")]
    story.append(bullets([
        "<b>TimescaleDB tick store</b> — replace SQLite with TimescaleDB for efficient "
        "continuous aggregates, multi-day VWAP queries, and month-over-month regime analysis "
        "without full-table scans.",
        "<b>Position reconciliation job</b> — nightly diff between broker-reported positions "
        "and locally cached state to detect sync drift, missed fills, or corporate actions.",
        "<b>Options Greeks dashboard</b> — pull IV, delta, gamma, theta for Kite F&O positions "
        "and surface a live Greeks table with expiry countdown timers.",
        "<b>Streamlit WebSocket push</b> — replace poll-based cache TTL with a true WebSocket "
        "push so holdings update on every tick without a full page reload.",
    ]))
    story.append(sp(6))

    story += [h2("7.2  AI Differentiators")]
    story.append(bullets([
        "<b>Anomaly-to-news pipeline</b> — when get_tick_anomalies fires, automatically call a "
        "web-search tool, attach the top 3 relevant headlines to the Claude context, and "
        "explain the price move with cited sources.",
        "<b>Voice morning brief</b> — pipe daily_brief() output through a TTS API (ElevenLabs "
        "or AWS Polly) and deliver as an audio notification before market open.",
        "<b>NL order preview</b> (read-only) — convert natural language ('show me what 10 more "
        "AAPL shares would do to my portfolio') into a structured preview showing new weight, "
        "new risk score delta, and estimated cost — displayed for review, never submitted.",
        "<b>Backtester integration</b> — feed tick history from TimescaleDB into a vectorbt "
        "backtest triggered by a plain-English strategy description and surface the equity "
        "curve inside the dashboard.",
        "<b>Conversational portfolio journal</b> — after each REPL session, auto-summarise the "
        "conversation into a dated entry; Claude can later answer 'how has my risk score "
        "trended over the last month?' using its own historical outputs as context.",
    ]))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # 8. SAMPLE AI OUTPUTS
    # ──────────────────────────────────────────────────────────────────────────
    story += [h1("8. Sample AI Outputs"), hr()]

    story += [h2("8.1  Natural-Language Q&A")]
    story.append(p("<b>Q:</b> What is my total unrealised P&amp;L in USD today?"))
    story.append(p(
        "<b>A (Claude):</b> Your combined unrealised P&amp;L is <b>₹8,202.74 / $98.23</b> — "
        "₹6,313.50 from Kite positions (ITC and TCS leading) and ₹1,889.24 from your IBKR book "
        "(AAPL +$82.10, MSFT +$86.34, GOOGL +$24.82). The only drag is HDFCBANK at -₹339."
    ))
    story.append(sp(8))

    story += [h2("8.2  Risk Report")]
    story.append(p("<b>Prompt:</b> <code>python run.py --task 9 --risk</code>"))
    story.append(p(
        "<b>A (Claude):</b> Risk score: <b>31/100 (MODERATE)</b>. Your portfolio is reasonably "
        "diversified across 8 positions (HHI = 18.4) but carries meaningful sector concentration "
        "— Technology accounts for 55% of total value (HHI = 42.1). "
        "Broker split is skewed: 78% is held at Kite vs 22% at IBKR (HHI = 61.0). "
        "The only unrealised loss is HDFCBANK (-₹339, 0.4% of portfolio), so drawdown risk "
        "is minimal. To reduce the top risk factor, consider diversifying the Technology "
        "overweight into other sectors such as Energy or FMCG."
    ))
    story.append(sp(8))

    story += [h2("8.3  Tick Anomaly Detection")]
    story.append(table(
        [["symbol", "latest_ltp", "mean_ltp", "std_ltp", "z_score", "direction"],
         ["ITC", "520.00", "450.31", "5.0384", "13.831", "SPIKE ▲"]],
        col_widths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm],
    ))
    story.append(sp(4))
    story.append(p(
        "<b>Claude's analysis:</b> ITC's latest tick of ₹520 is 13.8 standard deviations above "
        "the rolling mean of ₹450.31 — an extreme outlier almost certainly representing a "
        "data-feed error or circuit-breaker event rather than genuine price discovery. "
        "You hold 100 shares of ITC (Kite), so if genuine, your unrealised P&amp;L would "
        "increase by approximately ₹5,785. Recommend waiting for the next 2-3 ticks to "
        "confirm before drawing conclusions."
    ))
    story.append(sp(10))

    story += [h2("8.4  Daily Brief")]
    story.append(bullets([
        "<b>Total portfolio value:</b> ₹8,97,312 / $10,747 (USD/INR = 83.50).",
        "<b>Unrealised P&amp;L:</b> +₹8,202.74 / +$98.23 — portfolio is in the green overall.",
        "<b>Top gainer:</b> ITC +₹3,215 (100 shares, avg ₹430 vs LTP ₹462.15).",
        "<b>Top loser:</b> HDFCBANK -₹339 (15 shares, avg ₹1,610 vs LTP ₹1,587.40).",
        "<b>Sector overweight:</b> Technology at 55% of total value — TCS and INFY are the main drivers.",
        "<b>Market regime:</b> RANGING — tick data shows low z-score dispersion and no clear directional trend.",
        "<b>Risk score:</b> 31/100 (MODERATE) — sector concentration is the top driver.",
        "<b>Observation:</b> IBKR book is all-green (+$193.26 combined); US tech positions benefiting from overnight gains.",
    ]))

    # ──────────────────────────────────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=_cover_page,
        onLaterPages=_on_page,
    )
    print(f"PDF written → {OUTPUT}")


if __name__ == "__main__":
    build()
