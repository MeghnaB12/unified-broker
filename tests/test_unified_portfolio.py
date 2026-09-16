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


def test_nonzero_kite_positions_are_normalized():
    positions = pd.DataFrame(
        [
            {
                "symbol": "INFY",
                "qty": 3,
                "avg_cost": 1400.0,
                "ltp": 1500.0,
                "market_value": 4500.0,
                "unrealised_pnl": 300.0,
            }
        ]
    )

    result = portfolio.build_unified_portfolio(_empty(), positions, _empty(), usd_inr=90.0)
    infy = result.iloc[0]

    assert infy["broker"] == "Kite"
    assert infy["market_value_inr"] == 4500.0
    assert infy["market_value_usd"] == 50.0
    assert infy["unrealised_pnl_usd"] == 3.33


def test_zero_quantity_kite_positions_are_ignored():
    positions = pd.DataFrame(
        [{"symbol": "INFY", "qty": 0, "ltp": 1500.0, "unrealised_pnl": 0.0}]
    )

    result = portfolio.build_unified_portfolio(_empty(), positions, _empty(), usd_inr=80.0)

    assert result.empty


def test_ibkr_inr_and_unknown_currency_paths_are_explicit():
    ibkr = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "qty": 1,
                "currency": "INR",
                "avg_cost": 2500.0,
                "mkt_price": 2600.0,
                "mkt_value": 2600.0,
                "unrealised_pnl": 100.0,
            },
            {
                "symbol": "SAP",
                "qty": 1,
                "currency": "EUR",
                "avg_cost": 100.0,
                "mkt_price": 110.0,
                "mkt_value": 110.0,
                "unrealised_pnl": 10.0,
            },
        ]
    )

    result = portfolio.build_unified_portfolio(_empty(), _empty(), ibkr, usd_inr=80.0)
    reliance = result[result["symbol"] == "RELIANCE"].iloc[0]
    sap = result[result["symbol"] == "SAP"].iloc[0]

    assert reliance["market_value_inr"] == 2600.0
    assert reliance["market_value_usd"] == 32.5
    assert sap["market_value_usd"] == 110.0
    assert sap["market_value_inr"] == 8800.0


def test_fx_api_success_returns_live_rate(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"rates": {"INR": 86.75}}

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: Response())

    assert portfolio.get_live_usd_inr() == 86.75


def test_fx_api_failure_uses_configured_fallback(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("requests.get", fail)
    monkeypatch.setattr(portfolio, "USD_INR_FALLBACK", 84.25)

    assert portfolio.get_live_usd_inr() == 84.25
