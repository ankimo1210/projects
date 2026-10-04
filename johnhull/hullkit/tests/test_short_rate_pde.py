"""§31.1 risk-neutral path discounting, PDE and stochastic-flat contradiction."""

import importlib
import math

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._short_rate_pde")


def test_constant_rate_path_discount_zero_yield_and_terminal_condition():
    grid = np.linspace(0, 3, 65)
    rates = np.full((5, 65), 0.04)
    discounts = model().discounted_path_values(rates, grid)
    assert discounts == pytest.approx(np.full(5, math.exp(-0.12)), rel=1e-14)
    assert model().zero_yield(discounts, 3) == pytest.approx(np.full(5, 0.04), abs=1e-14)
    assert model().gaussian_drift_bond(0.04, 0, 0, 0) == pytest.approx(1)


@pytest.mark.parametrize(
    "r,drift,sigma,T", [(0.04, 0, 0.02, 3), (-0.01, 0.002, 0.03, 2), (0.03, -0.003, 0.01, 5)]
)
def test_gaussian_bond_matches_independent_integrated_rate_mc_and_pde(r, drift, sigma, T):
    target = model().gaussian_drift_bond(r, drift, sigma, T)
    rng = np.random.default_rng(3112026)
    n = 65536
    steps = 128
    dt = T / steps
    W = np.cumsum(rng.standard_normal((n, steps)) * math.sqrt(dt), axis=1)
    times = np.linspace(0, T, steps + 1)
    rates = np.c_[np.full(n, r), r + drift * times[1:] + sigma * W]
    samples = model().discounted_path_values(rates, times)
    se = samples.std(ddof=1) / math.sqrt(n)
    assert abs(samples.mean() - target) <= 5 * se
    h = 1e-4

    def value(rate, tau):
        return math.exp(-rate * tau - 0.5 * drift * tau * tau + sigma * sigma * tau**3 / 6)

    vt = -(value(r, T + h) - value(r, T - h)) / (2 * h)
    vr = (value(r + h, T) - value(r - h, T)) / (2 * h)
    vrr = (value(r + h, T) - 2 * value(r, T) + value(r - h, T)) / h**2
    residual = model().short_rate_pde_residual(vt, vr, vrr, target, r, drift, sigma)
    assert abs(residual) < 1e-8
    assert target > math.exp(
        -r * T - 0.5 * drift * T * T
    )  # discount expectation != discount at mean


def test_flat_curve_candidate_cannot_have_stochastic_short_rate_at_all_horizons():
    horizons = np.array([0.5, 1, 2, 5])
    r = 0.03
    m = 0.002
    s = 0.01
    value = np.exp(-r * horizons)
    residual = model().flat_curve_pde_residual(r, horizons, m, s)
    assert residual == pytest.approx(
        value * (-m * horizons + 0.5 * s * s * horizons * horizons), abs=1e-14
    )
    assert np.any(abs(residual) > 1e-4)
    # Solving the polynomial identity at two nonzero horizons forces m=s^2=0.
    coefficients = np.column_stack([-horizons[:2], 0.5 * horizons[:2] ** 2])
    assert np.linalg.solve(coefficients, np.zeros(2)) == pytest.approx([0, 0], abs=1e-15)
    assert model().flat_curve_pde_residual(r, horizons, 0, 0) == pytest.approx(np.zeros(4))


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.gaussian_drift_bond(0.03, 0, 0.01, -1),
        lambda m: m.zero_yield(0.9, 0),
        lambda m: m.discounted_path_values([[0.03, 0.04]], [1, 0]),
    ],
)
def test_invalid_mathematical_domain_rejected(call):
    with pytest.raises(ValueError):
        call(model())
