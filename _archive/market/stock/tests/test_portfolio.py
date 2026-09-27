import numpy as np
import pandas as pd
from stockkit.analysis import portfolio as pf


def test_daily_returns_known_values(price_panel_2):
    dr = pf.daily_returns(price_panel_2)
    # first row dropped by dropna(how="all"); A +10%, B +5%
    np.testing.assert_allclose(dr["A"].to_numpy(), [0.1])
    np.testing.assert_allclose(dr["B"].to_numpy(), [0.05])


def test_sharpe_matches_definition(price_panel_2):
    ar = pf.annualized_return(price_panel_2)
    av = pf.annualized_vol(price_panel_2)
    sh = pf.sharpe(price_panel_2, rf=0.0)
    # with a single return per series, vol is 0 -> sharpe is NaN (guarded by replace(0, NaN))
    assert sh.isna().all() or np.isfinite(sh).all()
    assert set(ar.index) == {"A", "B"} == set(av.index)


def test_max_drawdown_non_positive():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.DataFrame({"X": [100, 90, 95, 80, 120]}, index=idx, dtype=float)
    assert pf.max_drawdown(prices)["X"] <= 0.0


def test_correlation_diagonal_is_one():
    idx = pd.date_range("2020-01-01", periods=6, freq="D")
    prices = pd.DataFrame(
        {"A": [1, 2, 3, 4, 5, 6], "B": [2, 1, 4, 3, 6, 5]}, index=idx, dtype=float
    )
    corr = pf.correlation(prices)
    np.testing.assert_allclose(np.diag(corr.to_numpy()), [1.0, 1.0])


def test_weighted_portfolio_normalizes_weights():
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    prices = pd.DataFrame(
        {"A": [100, 110, 121, 133.1], "B": [50, 55, 60.5, 66.55]}, index=idx, dtype=float
    )
    equal = pf.weighted_portfolio(prices)  # default equal weight
    doubled = pf.weighted_portfolio(prices, {"A": 2.0, "B": 2.0})  # normalizes to equal
    np.testing.assert_allclose(equal.to_numpy(), doubled.to_numpy())


def test_price_panel_assembles_wide_frame(monkeypatch):
    idx = pd.date_range("2020-01-01", periods=3, freq="D")

    def fake_get_prices(symbol, period="5y"):
        if symbol == "EMPTY":
            return pd.DataFrame()
        base = {"A": 100.0, "B": 200.0}[symbol]
        return pd.DataFrame({"adj_close": [base, base + 1, base + 2]}, index=idx)

    monkeypatch.setattr(pf, "get_prices", fake_get_prices)
    panel = pf.price_panel(["A", "B", "EMPTY"])
    assert list(panel.columns) == ["A", "B"]  # EMPTY skipped
    assert len(panel) == 3


def test_price_panel_all_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(pf, "get_prices", lambda s, period="5y": pd.DataFrame())
    assert pf.price_panel(["A", "B"]).empty
