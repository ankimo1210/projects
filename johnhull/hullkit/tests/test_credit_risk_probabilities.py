"""Hull §24.2 historical PD vs interval/conditional probabilities and annual hazard."""

import math

import numpy as np
import pytest
from hullkit import _credit_risk as c
from scipy.integrate import solve_ivp


def test_source_table_24_1_probability_arithmetic():
    bbb = c.historical_pd([1, 2], [0.0016, 0.0045])
    assert 100 * bbb["interval_pd"][1] == pytest.approx(0.29)
    ccc = c.historical_pd([2, 3], [0.3664, 0.4141])
    assert 100 * ccc["interval_pd"][1] == pytest.approx(4.77)
    assert 100 * ccc["survival"][0] == pytest.approx(63.36)
    assert 100 * ccc["conditional_pd"][1] == pytest.approx(7.53, abs=0.005)
    assert ccc["measure"] == "P"


def test_piecewise_hazard_survival_against_independent_ode():
    data = c.historical_pd([1, 2, 4], [0.02, 0.07, 0.14])
    prior_time, prior_survival = 0, 1
    for time, rate, target in zip([1, 2, 4], data["forward_hazard"], data["survival"], strict=True):
        reference = solve_ivp(
            lambda t, y, rate=rate: -rate * y,
            [prior_time, time],
            [prior_survival],
            rtol=1e-11,
            atol=1e-13,
        )
        assert reference.y[0, -1] == pytest.approx(target, abs=1e-10)
        assert data["curve"].survival(time) == pytest.approx(target)
        prior_time, prior_survival = time, target
    assert data["average_hazard"] == pytest.approx(
        [-math.log(1 - p) / t for t, p in zip([1, 2, 4], [0.02, 0.07, 0.14], strict=True)]
    )


def test_constant_hazard_and_conditional_probability_composition():
    rates = c.constant_pd(0.02, 3)
    assert rates["survival"] == pytest.approx(math.exp(-0.06))
    assert rates["pd"] == pytest.approx(1 - math.exp(-0.06))
    table = c.historical_pd([1, 2, 3], 1 - np.exp(-0.02 * np.arange(1, 4)))
    assert table["forward_hazard"] == pytest.approx([0.02] * 3)
    assert np.prod(1 - table["conditional_pd"]) == pytest.approx(rates["survival"])
    assert c.constant_pd(0, 3)["pd"] == 0


def test_invalid_negative_hazard_and_decreasing_cumulative_pd():
    with pytest.raises(ValueError):
        c.constant_pd(-0.02, 1)
    with pytest.raises(ValueError):
        c.historical_pd([1, 2], [0.1, 0.05])
