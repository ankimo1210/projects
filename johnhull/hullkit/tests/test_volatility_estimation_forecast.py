"""Hull §23.6 Tables23.3/4 checked by continuous-time quadrature and finite differences."""

import math

import numpy as np
import pytest
from hullkit import _volatility_estimation as v
from scipy.integrate import quad

PARAMS = (0.0000039818, 0.223793, 0.747577)
DAYS = [10, 30, 50, 100, 500]


def test_source_expected_variances_10_and_100_days():
    assert v.expected_variance(0.0003, 10, *PARAMS) == pytest.approx(0.0002594, abs=5e-8)
    assert v.expected_variance(0.0003, 100, *PARAMS) == pytest.approx(0.0001479, abs=5e-8)
    current = 0.0003
    omega, alpha, beta = PARAMS
    for _ in range(10):
        current = omega + (alpha + beta) * current
    assert v.expected_variance(0.0003, 10, *PARAMS) == pytest.approx(current)


def test_source_table_23_3_and_independent_variance_integral():
    printed = [26.5, 24.9, 23.8, 22.0, 19.5]
    for days, percent in zip(DAYS, printed, strict=True):
        result = v.garch_term_vol(0.0003, days, *PARAMS)
        assert 100 * result["annual_vol"] == pytest.approx(percent, abs=0.05)
        omega, alpha, beta = PARAMS
        long = omega / (1 - alpha - beta)
        reference = (
            quad(
                lambda time, long=long, alpha=alpha, beta=beta: (
                    long + math.exp(time * math.log(alpha + beta)) * (0.0003 - long)
                ),
                0,
                days,
            )[0]
            / days
        )
        assert result["average_variance"] == pytest.approx(reference, abs=1e-15)


def test_source_table_23_4_and_annual_vol_sensitivity():
    spot_vol = np.sqrt(252 * 0.0003)
    for days, impact in zip(DAYS, [0.90, 0.74, 0.61, 0.41, 0.10], strict=True):
        sensitivity = v.garch_vol_sensitivity(0.0003, days, *PARAMS)
        assert sensitivity == pytest.approx(impact, abs=0.005)  # +1 percentage point input
        epsilon = 1e-5
        up = v.garch_term_vol((spot_vol + epsilon) ** 2 / 252, days, *PARAMS)["annual_vol"]
        down = v.garch_term_vol((spot_vol - epsilon) ** 2 / 252, days, *PARAMS)["annual_vol"]
        assert sensitivity == pytest.approx((up - down) / (2 * epsilon), rel=1e-8)


def test_zero_horizon_ewma_limit_and_near_unit_persistence():
    zero = v.garch_term_vol(0.0003, 0, *PARAMS)
    assert zero["annual_vol"] == pytest.approx(np.sqrt(252 * 0.0003))
    assert v.garch_term_vol(0.0003, 100, 0, 0.06, 0.94)["average_variance"] == pytest.approx(0.0003)
    p = 1 - 1e-12
    near = v.garch_term_vol(0.0003, 20, (1 - p) * 0.0002, 0.1, p - 0.1)
    assert near["average_variance"] == pytest.approx(0.0003, rel=1e-9)
    assert v.garch_vol_sensitivity(0, 10, 0, 0.1, 0.8) > 0
