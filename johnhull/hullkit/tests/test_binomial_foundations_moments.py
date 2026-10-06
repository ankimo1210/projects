"""Hull GE section 13.7: exact mean and first-order variance matching."""

import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations


def test_crr_moments_match_independent_two_point_distribution():
    result = foundations.crr_moments(0.3, 0.4, 0.05)
    p, up, down = result["probability"], result["up"], result["down"]
    mean = np.average([up, down], weights=[p, 1 - p])
    variance = np.average((np.array([up, down]) - mean) ** 2, weights=[p, 1 - p])
    assert result["mean"] == pytest.approx(math.exp(0.05 * 0.4), abs=1e-12)
    assert result["mean"] == pytest.approx(mean, abs=1e-12)
    assert result["variance"] == pytest.approx(variance, abs=1e-12)
    assert result["variance"] != pytest.approx(result["lognormal_variance"], abs=1e-5)


def test_source_first_order_equation_and_independent_taylor_error_coefficient():
    sigma, drift = 0.3, 0.05
    # Expanding a(u+d)-a^2-1 gives this h^2 coefficient independently.
    coefficient = -(drift**2) + drift * sigma**2 + sigma**4 / 12
    exact_difference = -(drift**2) - drift * sigma**2 - 5 * sigma**4 / 12
    for dt in [1e-3, 5e-4, 1e-4]:
        result = foundations.crr_moments(sigma, dt, drift)
        assert (result["variance"] - sigma * sigma * dt) / dt**2 == pytest.approx(
            coefficient, abs=2e-6
        )
        assert result["variance_error"] / dt**2 == pytest.approx(exact_difference, abs=2e-6)


def test_measure_change_keeps_moves_and_limiting_volatility_but_not_finite_variance():
    q = foundations.crr_moments(0.3, 0.01, 0.05)
    p = foundations.crr_moments(0.3, 0.01, 0.1)
    assert [p["up"], p["down"]] == pytest.approx([q["up"], q["down"]], abs=1e-12)
    assert p["probability"] > q["probability"]
    assert abs(p["variance"] - q["variance"]) > 1e-8
    for drift in [0.05, 0.1]:
        fine = foundations.crr_moments(0.3, 1e-4, drift)
        assert fine["variance"] / 1e-4 == pytest.approx(0.3**2, abs=1e-6)


def test_zero_time_or_volatility_and_unattainable_drift_are_rejected():
    for sigma, dt, drift in [(0, 0.1, 0.05), (0.3, 0, 0.05), (0.01, 1, 0.5)]:
        with pytest.raises(ValueError):
            foundations.crr_moments(sigma, dt, drift)
