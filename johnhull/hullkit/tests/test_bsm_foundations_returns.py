"""Hull GE 15.3: realized returns, reinvestment and Jensen's distinction."""

import math
from fractions import Fraction

import numpy as np
import pytest
from hullkit import _bsm_foundations as foundations
from scipy.integrate import quad
from scipy.stats import lognorm

RETURNS = [0.15, 0.20, 0.30, -0.20, 0.25]


def test_hull_five_year_fund_arithmetic_and_geometric_returns():
    result = foundations.realized_return_summary(100, RETURNS)
    assert result["arithmetic_mean"] == pytest.approx(0.14)
    assert result["balances"][-1] == pytest.approx(179.40)
    assert result["constant_mean_final"] == pytest.approx(192.54, abs=0.005, rel=0)
    assert result["geometric_mean"] == pytest.approx(0.124, abs=0.0005, rel=0)


def test_fund_against_independent_exact_cash_ledger():
    wealth = Fraction(100)
    ledger = [float(wealth)]
    for r in [
        Fraction(15, 100),
        Fraction(20, 100),
        Fraction(30, 100),
        Fraction(-20, 100),
        Fraction(25, 100),
    ]:
        wealth += wealth * r
        ledger.append(float(wealth))
    result = foundations.realized_return_summary(100, RETURNS)
    assert np.allclose(result["balances"], ledger, rtol=0, atol=1e-12)
    assert (1 + result["geometric_mean"]) ** 5 * 100 == pytest.approx(float(wealth), abs=1e-12)


def test_gbm_jensen_gap_against_independent_price_density():
    law = foundations.stock_distribution(20, 0.20, 0.40, 1)
    density = lognorm(s=0.4, scale=20 * math.exp(0.12))
    expected_log = quad(lambda s: math.log(s) * density.pdf(s), 0, math.inf)[0]
    expected_price = quad(lambda s: s * density.pdf(s), 0, math.inf)[0]
    assert law["log_mean"] == pytest.approx(expected_log, abs=1e-10)
    assert math.log(expected_price) - expected_log == pytest.approx(0.08, abs=1e-10)


def test_total_loss_and_impossible_simple_return():
    assert foundations.realized_return_summary(100, [-1, 0.2])["geometric_mean"] == -1
    with pytest.raises(ValueError):
        foundations.realized_return_summary(100, [-1.1])
