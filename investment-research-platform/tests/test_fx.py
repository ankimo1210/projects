"""FX / base-currency conversion: correct multiply, no forward-fill, quote inversion."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from irp.data import fx_adjusted_returns, invert_quote, to_base_currency


def test_to_base_currency_converts_only_foreign_columns():
    idx = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.DataFrame({"SPY": [400.0, 410.0, 420.0], "7203": [2000.0, 2100.0, 2200.0]}, index=idx)
    # USD per JPY ~ 1/150
    fx = pd.DataFrame({"JPY": [1 / 150, 1 / 150, 1 / 150]}, index=idx)
    out = to_base_currency(prices, {"SPY": "USD", "7203": "JPY"}, fx, base="USD")
    assert out["SPY"].tolist() == [400.0, 410.0, 420.0]  # base asset unchanged
    assert out["7203"].iloc[0] == pytest.approx(2000.0 / 150)  # converted to USD


def test_to_base_currency_does_not_fill_missing_fx():
    idx = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.DataFrame({"7203": [2000.0, 2100.0, 2200.0]}, index=idx)
    fx = pd.DataFrame({"JPY": [1 / 150, np.nan, 1 / 150]}, index=idx)  # gap on day 2
    out = to_base_currency(prices, {"7203": "JPY"}, fx, base="USD")
    assert np.isnan(out["7203"].iloc[1])  # missing FX -> NaN, never forward-filled


def test_unknown_currency_is_nan_not_guessed():
    idx = pd.bdate_range("2024-01-01", periods=2)
    prices = pd.DataFrame({"X": [10.0, 11.0]}, index=idx)
    out = to_base_currency(prices, {"X": "EUR"}, pd.DataFrame(index=idx), base="USD")
    assert out["X"].isna().all()


def test_invert_quote():
    s = pd.Series([150.0, 0.0, 100.0])  # USDJPY (JPY per USD)
    inv = invert_quote(s)
    assert inv.iloc[0] == pytest.approx(1 / 150)
    assert np.isnan(inv.iloc[1])  # 0 -> NaN, not inf


def test_fx_adjusted_returns_compounds():
    r = pd.Series([0.10, -0.05])
    f = pd.Series([0.02, 0.01])
    out = fx_adjusted_returns(r, f)
    assert out.iloc[0] == pytest.approx(1.10 * 1.02 - 1)
    assert out.iloc[1] == pytest.approx(0.95 * 1.01 - 1)
