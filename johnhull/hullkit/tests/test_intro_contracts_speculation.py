"""Hull §1.8 capital, quantity and speculation profit comparisons."""

import math

import numpy as np
import pytest
from hullkit import _intro_contracts as c
from scipy.stats import norm


def test_source_fx_speculation_all_six_amounts():
    a = c.speculation_comparison(1.2220, 1.2223, [1.3, 1.2], units=250000, initial_margin=20000)
    assert [a["spot_outlay"], a["initial_margin"]] == pytest.approx([305500, 20000])
    assert a["spot_profit"] == pytest.approx([19500, -5500])
    assert a["futures_profit"] == pytest.approx([19425, -5575])
    assert 4 * 62500 == pytest.approx(250000)


def test_source_stock_call_speculation_all_seven_amounts():
    a = c.stock_option_speculation(20, [27, 15], 22.5, 1, 2000)
    assert a["stock_profit"] == pytest.approx([700, -500])
    assert a["option_payoff"][0] / a["option_units"] == pytest.approx(4.5)
    assert a["option_payoff"][0] == pytest.approx(9000)
    assert a["option_profit"] == pytest.approx([7000, -2000])
    assert a["option_profit"][0] / a["stock_profit"][0] == pytest.approx(10)
    assert [a["stock_units"], a["option_units"], a["option_contracts"]] == pytest.approx(
        [100, 2000, 20]
    )


def test_independent_analytic_expectation_against_seeded_mc():
    # Synthetic lognormal law; independent of the historical input scenarios.
    mean, sd, k = 24, 0.3, 22.5
    z = np.random.default_rng(108).standard_normal(200000)
    terminal = mean * np.exp(-(sd**2) / 2 + sd * z)
    a = c.stock_option_speculation(20, terminal, k, 1, 2000)
    d1 = (math.log(mean / k) + sd**2 / 2) / sd
    call = mean * norm.cdf(d1) - k * norm.cdf(d1 - sd)
    for samples, expected in [
        (a["stock_profit"], 100 * (mean - 20)),
        (a["option_profit"], 2000 * (call - 1)),
    ]:
        se = np.std(samples, ddof=1) / math.sqrt(len(z))
        assert abs(np.mean(samples) - expected) < 6 * se
    f = c.speculation_comparison(20, 21, terminal, units=100, initial_margin=200)
    assert abs(np.mean(f["futures_profit"]) - 100 * (mean - 21)) < 6 * np.std(
        f["futures_profit"], ddof=1
    ) / math.sqrt(len(z))
