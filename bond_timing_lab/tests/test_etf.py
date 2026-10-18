import pandas as pd
import pytest
from bond_timing.data.etf import daily_returns, monthly_total_returns, parse_prices


def test_parse_prices_round_trip():
    prices = parse_prices(b"date,close\n2020-01-30,100\n2020-01-31,101\n")
    assert prices.index[1] == pd.Timestamp("2020-01-31") and prices.iloc[1] == 101.0


def test_monthly_total_returns_drop_a_month_in_progress():
    index = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-28", "2020-03-10"])
    prices = pd.Series([100.0, 101.0, 103.02, 104.0], index=index)
    returns = monthly_total_returns(prices)
    assert list(returns.index.astype(str)) == ["2020-02"]
    assert returns.iloc[0] == pytest.approx(103.02 / 101.0 - 1)
    assert daily_returns(prices).iloc[0] == pytest.approx(0.01)
