"""
Unified Broker — top-level runner
──────────────────────────────────
Convenience script to exercise all tasks from the command line.

Usage:
    python run.py --task 1          # Kite auth & session
    python run.py --task 2          # Kite portfolio
    python run.py --task 3          # Kite tick stream (Ctrl-C to stop)
    python run.py --task 3 --duration 60
    python run.py --task 4          # IBKR auth
    python run.py --task 5          # IBKR portfolio
    python run.py --task 6          # IBKR market data (60 s)
    python run.py --task 7          # Unified portfolio view
    python run.py --task 8          # Launch Streamlit dashboard
    python run.py --task 9          # AI assistant (interactive)
    python run.py --task 9 --brief  # AI daily brief
    python run.py --task 9 --anomaly
    python run.py --task 9 --ask "What is my largest position?"
"""
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Unified Broker runner")
    parser.add_argument("--task",     type=int, required=True,
                        choices=range(1, 10), metavar="N",
                        help="Task number to run (1-9)")
    parser.add_argument("--duration", type=int, default=0,
                        help="Duration in seconds (tasks 3, 6)")
    parser.add_argument("--brief",    action="store_true",
                        help="AI daily brief (task 9)")
    parser.add_argument("--anomaly",  action="store_true",
                        help="AI tick anomaly scan (task 9)")
    parser.add_argument("--risk",     action="store_true",
                        help="AI portfolio risk report (task 9)")
    parser.add_argument("--ask",      type=str, default="",
                        help="One-shot AI question (task 9)")
    args = parser.parse_args()

    if args.task == 1:
        from kite.auth import get_kite_client
        from datetime import datetime
        kite    = get_kite_client()
        profile = kite.profile()
        print(f"\n✓ Logged in as: {profile['user_name']} ({profile['email']})")
        print(f"  Broker : {profile['broker']}")
        print(f"  TS     : {datetime.now().isoformat()}")

    elif args.task == 2:
        from kite.auth      import get_kite_client
        from kite.portfolio import portfolio_summary
        kite = get_kite_client()
        portfolio_summary(kite)

    elif args.task == 3:
        from kite.ticks import stream_ticks
        stream_ticks(duration_seconds=args.duration)

    elif args.task == 4:
        import time
        from ibkr.auth import get_ibkr_client
        ib = get_ibkr_client()
        print(f"\n✓ Connected  accounts={ib.managedAccounts()}")
        print("  [reconnect test] disconnecting…")
        ib.disconnect()
        time.sleep(3)
        ib2 = get_ibkr_client()
        print(f"  Reconnected ✓  accounts={ib2.managedAccounts()}")
        ib2.disconnect()

    elif args.task == 5:
        from ibkr.auth      import get_ibkr_client
        from ibkr.portfolio import portfolio_summary
        ib = get_ibkr_client()
        portfolio_summary(ib)
        ib.disconnect()

    elif args.task == 6:
        from ibkr.market_data import stream_market_data
        stream_market_data(duration=max(args.duration, 60))

    elif args.task == 7:
        from kite.auth       import get_kite_client
        from kite.portfolio  import fetch_holdings, fetch_positions as kite_pos
        from ibkr.auth       import get_ibkr_client
        from ibkr.portfolio  import fetch_positions as ibkr_pos
        from unified.portfolio import build_unified_portfolio, get_live_usd_inr, print_unified_summary

        kite          = get_kite_client()
        kite_holdings = fetch_holdings(kite)
        kite_net, _   = kite_pos(kite)

        ib       = get_ibkr_client()
        ibkr_p   = ibkr_pos(ib)
        ib.disconnect()

        usd_inr = get_live_usd_inr()
        unified = build_unified_portfolio(kite_holdings, kite_net, ibkr_p, usd_inr)
        print_unified_summary(unified, usd_inr)

    elif args.task == 8:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"],
            check=True,
        )

    elif args.task == 9:
        from ai.assistant import (
            _load_portfolio, daily_brief, risk_report, detect_tick_anomalies,
            explain_anomalies, interactive_repl, ask,
        )
        portfolio_data = _load_portfolio()

        if args.brief:
            print("\n" + daily_brief(portfolio_data))
        elif args.risk:
            print("\n" + risk_report(portfolio_data))
        elif args.anomaly:
            from rich.console import Console
            from rich.table   import Table
            console   = Console()
            anomalies = detect_tick_anomalies()
            if anomalies.empty:
                console.print("[green]No anomalies detected.[/green]")
            else:
                table = Table(title="Tick Anomalies", show_lines=True)
                for col in anomalies.columns:
                    table.add_column(col, style="yellow")
                for _, row in anomalies.iterrows():
                    table.add_row(*[str(v) for v in row])
                console.print(table)
                console.print("\n[bold]Claude's analysis:[/bold]")
                console.print(explain_anomalies(anomalies, portfolio_data))
        elif args.ask:
            answer, _ = ask(args.ask, portfolio_data)
            print(f"\n{answer}")
        else:
            interactive_repl(portfolio_data)


if __name__ == "__main__":
    main()
