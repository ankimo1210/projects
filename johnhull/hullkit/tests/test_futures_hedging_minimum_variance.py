"""Hull Table3.2 regression inputs and independent least squares/minimization."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h
from scipy.optimize import minimize_scalar

F = np.array(
    [
        0.021,
        0.035,
        -0.046,
        0.001,
        0.044,
        -0.029,
        -0.026,
        -0.029,
        0.048,
        -0.006,
        -0.036,
        -0.011,
        0.019,
        -0.027,
        0.029,
    ]
)
S = np.array(
    [
        0.029,
        0.020,
        -0.044,
        0.008,
        0.026,
        -0.019,
        -0.010,
        -0.007,
        0.043,
        0.011,
        -0.036,
        -0.018,
        0.009,
        -0.032,
        0.023,
    ]
)


def test_source_all_nine_values():
    a = h.minimum_variance_hedge(S, F, exposure_units=2e6, contract_units=42000)
    assert [a["sd_future"], a["sd_spot"]] == pytest.approx([0.0313, 0.0263], rel=0, abs=0.00005)
    assert a["rho"] == pytest.approx(0.928, rel=0, abs=0.0005)
    assert a["ratio"] == pytest.approx(0.78, rel=0, abs=0.005)
    assert a["contracts"] == pytest.approx(37, abs=0.5)
    day = h.hedge_contracts(0.8, 2e6 * 1.1, 42000 * 1.3)
    assert [
        day["exposure_value"],
        day["contract_value"],
        day["contracts"],
        day["rounded"],
    ] == pytest.approx([2200000, 54600, 32.23, 32], abs=0.005)


def test_independent_ols_variance_minimum_and_tailing():
    a = h.minimum_variance_hedge(S, F, exposure_units=2e6, contract_units=42000)
    slope = np.linalg.lstsq(np.c_[np.ones(15), F], S, rcond=None)[0][1]
    minimum = minimize_scalar(lambda b: np.var(S - b * F, ddof=1), bracket=(0, 1))
    assert a["ratio"] == pytest.approx(slope, abs=1e-12)
    assert a["ratio"] == pytest.approx(minimum.x, abs=1e-7)
    residual = S - slope * F
    assert 1 - np.var(residual, ddof=1) / np.var(S, ddof=1) == pytest.approx(a["effectiveness"])
    t = h.hedge_contracts(0.8, 2200000, 54600, growth=1.05)
    assert t["contracts"] == pytest.approx(30.699459, abs=1e-6)
