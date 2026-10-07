"""Hull Ex36.1 timing and independent rental density/coordinate references."""

import math

import numpy as np
import pytest
from hullkit import _real_options_foundations as r
from scipy.integrate import quad
from scipy.stats import norm


def test_source_rental_option_full_pricing_chain():
    a = r.rental_option(30, 0.12, 0.2, 0.3, 0.05, 2, 35, 100000, 5)
    assert a["annuity"] == pytest.approx(4.5355, rel=0, abs=0.00005)
    assert a["q_growth"] == pytest.approx(0.06)
    assert a["expected_rent"] == pytest.approx(33.82, rel=0, abs=0.005)
    assert [a["expected_payoff"], a["value"]] == pytest.approx([1501500, 1358600], rel=0, abs=50)
    assert a["value"] > 1000000


def test_independent_rental_integral_advance_payments_and_zero_volatility():
    a = r.rental_option(30, 0.12, 0.2, 0.3, 0.05, 2, 35, 100000, 5)
    location = math.log(30) + (0.06 - 0.2**2 / 2) * 2
    sd = 0.2 * math.sqrt(2)
    lower = (math.log(35) - location) / sd
    expected_unit = quad(
        lambda z: (math.exp(location + sd * z) - 35) * norm.pdf(z), lower, 12, epsabs=1e-11
    )[0]
    individual = sum(100000 * expected_unit * math.exp(-0.05 * (2 + year)) for year in range(5))
    assert a["value"] == pytest.approx(individual, rel=0, abs=1e-6)
    deterministic = r.rental_option(30, 0.12, 0, 0.3, 0.05, 2, 35, 100000, 5)
    cash = 100000 * max(30 * math.exp(0.24) - 35, 0)
    assert deterministic["value"] == pytest.approx(
        sum(cash * math.exp(-0.05 * (2 + year)) for year in range(5))
    )


def test_independent_factor_adjustment_rotation_and_traded_stock_limit():
    mu = np.array([0.12, 0.09])
    load = np.array([[0.2, 0.1], [-0.1, 0.3]])
    lam = np.array([0.3, -0.2])
    expected = np.array([0.12 - (0.2 * 0.3 + 0.1 * (-0.2)), 0.09 - (-0.1 * 0.3 + 0.3 * (-0.2))])
    assert r.risk_adjusted_drift(mu, load, lam) == pytest.approx(expected)
    rotation = np.array([[1, -1], [1, 1]]) / math.sqrt(2)
    assert r.risk_adjusted_drift(mu, load @ rotation, rotation.T @ lam) == pytest.approx(
        expected, abs=1e-14
    )
    assert r.risk_adjusted_drift([0.12], [[0.2]], [(0.12 - 0.05) / 0.2]) == pytest.approx([0.05])
