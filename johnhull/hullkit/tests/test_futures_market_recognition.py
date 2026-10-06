"""Hull §2.10 recognition versus physical cash settlement."""

import numpy as np
import pytest
from hullkit import _futures_market as f


def test_source_three_accounting_amounts():
    ordinary = f.recognized_futures_profit([350, 370, 380], units=5000)
    hedge = f.recognized_futures_profit([350, 370, 380], units=5000, hedge_accounting=True)
    assert ordinary["recognized"] == pytest.approx([1000, 500])
    assert hedge["recognized"] == pytest.approx([0, 1500])
    assert hedge["cash_profit"] == pytest.approx(ordinary["cash_profit"])


def test_independent_terminal_cash_and_period_linear_projection():
    prices = np.array([350.0, 340.0, 370.0, 380.0])
    a = f.recognized_futures_profit(prices, units=5000, hedge_accounting=True)
    total = (380 - 350) * 50
    projection = np.array([[0, 0, 0], [0, 0, 0], [1, 1, 1]])
    assert np.sum(a["cash_profit"]) == pytest.approx(total)
    assert a["recognized"] == pytest.approx(projection @ a["cash_profit"])
    assert f.recognized_futures_profit(prices, units=5000, side="short")[
        "recognized"
    ].sum() == pytest.approx(-total)
