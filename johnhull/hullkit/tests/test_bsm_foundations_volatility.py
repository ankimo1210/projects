"""Hull GE 15.4: all Table 15.1 rows, annualization and dividends."""

import math
from decimal import Decimal, localcontext
from itertools import pairwise

import numpy as np
import pytest
from hullkit import _bsm_foundations as foundations

PRICES = [
    20,
    20.1,
    19.9,
    20,
    20.5,
    20.25,
    20.9,
    20.9,
    20.9,
    20.75,
    20.75,
    21,
    21.1,
    20.9,
    20.9,
    21.25,
    21.4,
    21.4,
    21.25,
    21.75,
    22,
]
RELATIVES = [
    1.00500,
    0.99005,
    1.00503,
    1.02500,
    0.98780,
    1.03210,
    1,
    1,
    0.99282,
    1,
    1.01205,
    1.00476,
    0.99052,
    1,
    1.01675,
    1.00706,
    1,
    0.99299,
    1.02353,
    1.01149,
]
LOG_RETURNS = [
    0.00499,
    -0.01000,
    0.00501,
    0.02469,
    -0.01227,
    0.03159,
    0,
    0,
    -0.00720,
    0,
    0.01198,
    0.00475,
    -0.00952,
    0,
    0.01661,
    0.00703,
    0,
    -0.00703,
    0.02326,
    0.01143,
]


def test_all_table_15_1_rows_and_example_15_4_estimates():
    result = foundations.historical_volatility(PRICES, 1 / 252)
    assert result["price_relatives"] == pytest.approx(RELATIVES, abs=0.000005, rel=0)
    assert result["log_returns"] == pytest.approx(LOG_RETURNS, abs=0.000005, rel=0)
    assert [result["sum_returns"], result["sum_squares"], result["interval_sd"]] == pytest.approx(
        [0.09531, 0.00326, 0.01216], abs=0.000005, rel=0
    )
    assert [result["annual_vol"], result["vol_se"]] == pytest.approx(
        [0.193, 0.031], abs=0.0005, rel=0
    )


def test_table_against_independent_decimal_logs_and_expanded_variance():
    with localcontext() as context:
        context.prec = 40
        prices = [Decimal(str(s)) for s in PRICES]
        returns = [(b / a).ln() for a, b in pairwise(prices)]
        n = Decimal(len(returns))
        variance = (sum(u * u for u in returns) - sum(returns) ** 2 / n) / (n - 1)
        annual_vol = (variance * 252).sqrt()
    result = foundations.historical_volatility(PRICES, 1 / 252)
    assert np.allclose(result["log_returns"], [float(u) for u in returns], rtol=0, atol=3e-16)
    assert result["annual_vol"] == pytest.approx(float(annual_vol), abs=1e-14)
    assert result["vol_se"] == pytest.approx(float(annual_vol) / math.sqrt(40), abs=1e-14)


def test_dividend_adjustment_is_return_cashflow_not_deletion():
    adjusted = foundations.historical_volatility([100, 99, 101], 0.25, dividends=[1, 0])
    assert adjusted["log_returns"] == pytest.approx([0, math.log(101 / 99)], abs=1e-14)
    raw = foundations.historical_volatility([100, 99, 101], 0.25)
    assert adjusted["annual_vol"] < raw["annual_vol"]
    assert adjusted["annual_vol"] == pytest.approx(adjusted["interval_sd"] * 2)


def test_hull_weekly_small_move_uses_square_root_time():
    weekly = foundations.stock_distribution(50, 0, 0.3, 1 / 52)["log_sd"]
    four_weeks = foundations.stock_distribution(50, 0, 0.3, 4 / 52)["log_sd"]
    assert weekly == pytest.approx(0.0416, abs=0.00005, rel=0)
    assert 50 * weekly == pytest.approx(2.08, abs=0.005, rel=0)
    assert four_weeks == pytest.approx(2 * weekly)


@pytest.mark.parametrize("prices,dt", [([20, 21], 1 / 252), ([20, 21, 22], 0)])
def test_estimator_requires_two_returns_and_positive_interval(prices, dt):
    with pytest.raises(ValueError):
        foundations.historical_volatility(prices, dt)
