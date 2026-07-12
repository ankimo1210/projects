"""Tests for log-log regression and Hurst estimators."""

import numpy as np
import pytest
from rough_volatility.estimators import (
    ESTIMATORS,
    hurst_aggregated_variance,
    hurst_madogram,
    hurst_variogram,
    loglog_ols,
)
from rough_volatility.fbm import fbm_paths


def test_loglog_ols_recovers_exact_power_law() -> None:
    x = np.geomspace(0.01, 10.0, 20)
    y = 3.5 * x**1.7
    fit = loglog_ols(x, y)
    assert fit.slope == pytest.approx(1.7, abs=1e-12)
    assert fit.intercept == pytest.approx(np.log(3.5), abs=1e-12)
    assert fit.r_squared == pytest.approx(1.0, abs=1e-12)
    assert fit.slope_se < 1e-12


def test_loglog_ols_rejects_too_few_valid_points() -> None:
    with pytest.raises(ValueError):
        loglog_ols(np.array([1.0, 2.0]), np.array([1.0, 4.0]))


@pytest.mark.parametrize("h", [0.10, 0.50, 0.80])
def test_clean_fbm_hurst_recovery(h: float) -> None:
    result = fbm_paths(h, 8192, 24, 1.0, np.random.default_rng(round(h * 1000)))
    variogram = np.mean([hurst_variogram(path).h_hat for path in result.paths])
    madogram = np.mean([hurst_madogram(path).h_hat for path in result.paths])
    assert abs(variogram - h) < 0.03
    assert abs(madogram - h) < 0.03


def test_aggregated_variance_recovers_fgn_scaling() -> None:
    h = 0.25
    path = fbm_paths(h, 65_536, 1, 1.0, np.random.default_rng(40)).paths[0]
    estimate = hurst_aggregated_variance(np.diff(path))
    assert abs(estimate.h_hat - h) < 0.04
    assert estimate.fit.slope == pytest.approx(2 * estimate.h_hat - 2)


def test_estimator_registry_is_complete() -> None:
    assert set(ESTIMATORS) == {"variogram", "madogram", "aggregated_variance"}
