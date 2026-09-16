import pandas as pd

from unified import portfolio


def _empty() -> pd.DataFrame:
    return pd.DataFrame()


def test_build_unified_portfolio_converts_inr_and_usd_positions():
    kite = pd.DataFrame(
        [
            {
                "symbol": "TCS",
                "qty": 2,
                "avg_cost": 3500.0,
                "ltp": 3600.0,
                "market_value": 7200.0,
                "unrealised_pnl": 200.0,
            }
        ]
    )
    ibkr = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "qty": 1,
                "currency": "USD",
                "avg_cost": 200.0,
                "mkt_price": 210.0,
                "mkt_value": 210.0,
                "unrealised_pnl": 10.0,
            }
        ]
    )

    result = portfolio.build_unified_portfolio(kite, _empty(), ibkr, usd_inr=80.0)

    tcs = result[result["symbol"] == "TCS"].iloc[0]
    aapl = result[result["symbol"] == "AAPL"].iloc[0]

    assert tcs["market_value_inr"] == 7200.0
    assert tcs["market_value_usd"] == 90.0
    assert aapl["market_value_usd"] == 210.0
    assert aapl["market_value_inr"] == 16800.0
    assert aapl["unrealised_pnl_inr"] == 800.0


def test_zero_quantity_kite_positions_are_ignored():
    positions = pd.DataFrame(
        [{"symbol": "INFY", "qty": 0, "ltp": 1500.0, "unrealised_pnl": 0.0}]
    )

    result = portfolio.build_unified_portfolio(_empty(), positions, _empty(), usd_inr=80.0)

    assert result.empty


def test_fx_api_failure_uses_configured_fallback(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("requests.get", fail)
    monkeypatch.setattr(portfolio, "USD_INR_FALLBACK", 84.25)

    assert portfolio.get_live_usd_inr() == 84.25
