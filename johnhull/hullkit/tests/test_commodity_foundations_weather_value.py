"""Hull Ex35.4 and independent lognormal payoff integration/Monte Carlo."""

import math
from itertools import pairwise

import numpy as np
import pytest
from hullkit import _commodity_foundations as c
from scipy.integrate import quad
from scipy.stats import norm


def test_source_weather_pricing_chain_without_intermediate_rounding():
    a = c.lognormal_weather_call(710, 0.07, 700, 10000, 0.03, 1)
    assert [a["d1"], a["d2"]] == pytest.approx([0.2376, 0.1676], rel=0, abs=0.00005)
    assert [a["expected_payoff"], a["value"]] == pytest.approx([250900, 243400], rel=0, abs=50)
    b = c.lognormal_weather_call(697, 0.07, 700, 10000, 0.03, 1)
    assert [b["expected_payoff"], b["value"]] == pytest.approx([180400, 175100], rel=0, abs=50)
    # The distribution describes one month's total: time to payment changes
    # discounting, not the supplied .07 log standard deviation.
    delayed = c.lognormal_weather_call(710, 0.07, 700, 10000, 0.03, 4)
    assert delayed["expected_payoff"] == pytest.approx(a["expected_payoff"])
    assert delayed["value"] == pytest.approx(a["expected_payoff"] * math.exp(-0.12))


def test_independent_density_capped_distribution_and_fixed_seed_mc():
    rng = np.random.default_rng(3537)
    for mean, cap in [(710, None), (697, None), (710, 1500000)]:
        a = c.lognormal_weather_call(mean, 0.07, 700, 10000, 0.03, 1, cap=cap)
        location = math.log(mean) - 0.07**2 / 2

        def integrand(z, location=location, cap=cap):
            cash = 10000 * max(math.exp(location + 0.07 * z) - 700, 0)
            if cap is not None:
                cash = min(cash, cap)
            return cash * norm.pdf(z)

        split = [-12, (math.log(700) - location) / 0.07, 12]
        if cap is not None:
            split.insert(2, (math.log(700 + cap / 10000) - location) / 0.07)
        reference = sum(
            quad(integrand, left, right, epsabs=1e-5)[0] for left, right in pairwise(split)
        )
        assert a["expected_payoff"] == pytest.approx(reference, rel=0, abs=1e-5)
        indexes = rng.lognormal(location, 0.07, 160000)
        cash = 10000 * np.maximum(indexes - 700, 0)
        if cap is not None:
            cash = np.minimum(cash, cap)
        assert abs(cash.mean() - a["expected_payoff"]) <= 6 * cash.std(ddof=1) / math.sqrt(
            len(cash)
        )
    for mean, strike, tick, cap in [
        (800, 700, 10000, None),
        (800, 700, 10000, 500000),
        (0, 700, 10000, None),
    ]:
        a = c.lognormal_weather_call(mean, 0, strike, tick, 0.03, 1, cap=cap)
        cash = max(mean - strike, 0) * tick
        if cap is not None:
            cash = min(cash, cap)
        assert a["value"] == pytest.approx(cash * math.exp(-0.03))
