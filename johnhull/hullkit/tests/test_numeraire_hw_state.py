"""Independent conditional-rate integrals test the documented Q OU state."""

import math

import pytest
from hullkit import hull_white as hw
from scipy.integrate import quad

A, SIGMA, R0 = 0.2, 0.02, 0.04
CURVE = ([0.0, 1.0, 2.0, 5.0, 10.0], [R0] * 5)
PARAMS = hw.HullWhiteParams(A, SIGMA)


def _b(h):
    return -math.expm1(-A * h) / A


def _c(h):
    return 0.5 * SIGMA**2 * _b(h) ** 2


def _integrated_noise_variance(h):
    # Independent integral of the OU integral kernel, avoiding bond formula.
    return quad(lambda u: SIGMA**2 * _b(u) ** 2, 0, h, epsabs=1e-14, epsrel=1e-13)[0]


@pytest.mark.parametrize("t,u,state", [(0.25, 2.0, -0.015), (0.75, 4.0, 0.0), (2.0, 5.0, 0.01)])
def test_q_ou_bond_matches_conditional_integrated_rate(t, u, state):
    mean = state * _b(u - t) + quad(lambda s: R0 + _c(s), t, u, epsabs=1e-14, epsrel=1e-13)[0]
    variance = _integrated_noise_variance(u - t)
    expected = math.exp(-mean + 0.5 * variance)
    assert hw.hw_discount_bond(t, u, state, CURVE, PARAMS) == pytest.approx(
        expected, abs=1e-12, rel=0
    )


def test_q_discounted_conditional_bond_obeys_tower_identity():
    t, u = 2.0, 5.0
    b = _b(u - t)
    variance_x = SIGMA**2 * (-math.expm1(-2 * A * t)) / (2 * A)
    covariance_x_integral = _c(t)
    variance_total = (
        _integrated_noise_variance(t) + b * b * variance_x + 2 * b * covariance_x_integral
    )
    mean_integral = quad(lambda s: R0 + _c(s), 0, t, epsabs=1e-14, epsrel=1e-13)[0]
    discounted_mean = hw.hw_discount_bond(t, u, 0.0, CURVE, PARAMS) * math.exp(
        -mean_integral + 0.5 * variance_total
    )
    assert discounted_mean == pytest.approx(math.exp(-R0 * u), abs=1e-12, rel=0)
