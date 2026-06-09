import math

import pandas as pd
import pytest

import prepare


def test_sharpe_known_value():
    # ret = [0.01, 0.02, 0.03]: mean=0.02, std(ddof=1)=0.01
    ret = pd.Series([0.01, 0.02, 0.03])
    expected = 0.02 / 0.01 * math.sqrt(prepare.ANNUALIZATION)
    assert prepare._sharpe(ret) == pytest.approx(expected)


def test_sharpe_zero_std_is_zero():
    ret = pd.Series([0.005, 0.005, 0.005])
    assert prepare._sharpe(ret) == 0.0


def test_sharpe_too_short_is_zero():
    assert prepare._sharpe(pd.Series([0.01])) == 0.0


def test_max_drawdown():
    # equity: 1.1, 0.55, 0.55 -> trough 0.55 vs peak 1.1 -> -0.5
    ret = pd.Series([0.1, -0.5, 0.0])
    assert prepare._max_drawdown(ret) == pytest.approx(-0.5)
