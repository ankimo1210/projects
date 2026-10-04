"""HJM signed bond/forward identities and independent short-rate benchmarks."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._hjm_forward")


@pytest.mark.parametrize("a", [0, 0.1])
def test_signed_bond_loading_finite_forward_and_instantaneous_limit(a):
    m = model()
    t = 0.7
    T = 4.0
    s = 0.01

    def volatility(u, U):
        return np.array([s * math.exp(-a * (U - u))])

    loading = m.bond_diffusion(t, T, volatility)
    integral = quad(lambda u: s * math.exp(-a * (u - t)), t, T)[0]
    assert loading == pytest.approx([-integral], abs=1e-14)
    assert m.bond_diffusion(t, t, volatility) == pytest.approx([0], abs=1e-14)
    drift = m.hjm_forward_drift(t, T, volatility)
    expected = s * math.exp(-a * (T - t)) * integral
    assert drift == pytest.approx(expected, abs=1e-14)
    for h in [0.01, 0.001, 0.0001]:
        row = m.finite_forward_sde(t, T - h / 2, T + h / 2, volatility)
        assert row["drift"] == pytest.approx(expected, abs=1e-9)
        assert row["diffusion"] == pytest.approx(volatility(t, T), abs=1e-8)


def test_two_factors_bond_diffusion_derivative_and_covariance_drift():
    m = model()
    t = 0.3
    T = 3.0
    h = 1e-5

    def volatility(t, T):
        return np.array([0.01 * (1 + 0.1 * (T - t)), 0.02 * math.exp(-0.4 * (T - t))])

    rho = np.array([[1, -0.4], [-0.4, 1]])
    derivative = -(
        m.bond_diffusion(t, T + h, volatility) - m.bond_diffusion(t, T - h, volatility)
    ) / (2 * h)
    assert derivative == pytest.approx(volatility(t, T), rel=1e-9)
    v = m.bond_diffusion(t, T, volatility)
    finite = (
        m.bond_diffusion(t, T + h, volatility) @ rho @ m.bond_diffusion(t, T + h, volatility)
        - m.bond_diffusion(t, T - h, volatility) @ rho @ m.bond_diffusion(t, T - h, volatility)
    ) / (4 * h)
    assert m.hjm_forward_drift(t, T, volatility, correlation=rho) == pytest.approx(
        finite, abs=1e-12
    )
    assert m.hjm_forward_drift(t, T, volatility, correlation=rho) == pytest.approx(
        -volatility(t, T) @ rho @ v, abs=1e-14
    )


@pytest.mark.parametrize("a", [0, 0.15])
def test_discrete_hjm_discounted_bond_and_option_against_independent_gaussian_short_rate(a):
    m = model()
    E, U = 1.0, 3.0
    sigma = 0.01
    f0 = 0.04
    K = 0.93

    def vol(t, T):
        return np.array([sigma * math.exp(-a * (T - t))])

    grid = np.linspace(0, U, 193)
    times = grid[:65]
    row = m.simulate_hjm(
        times, grid, np.full(grid.size, f0), vol, 8192, np.random.default_rng(3312026)
    )
    mask = grid >= E
    bond = np.exp(-np.trapezoid(row["terminal_forwards"][:, mask], grid[mask], axis=1))
    discounted_bond = row["discounts"] * bond
    assert (
        abs(discounted_bond.mean() - math.exp(-f0 * U))
        < 5 * discounted_bond.std(ddof=1) / math.sqrt(bond.size) + 2e-5
    )
    # Independent Gaussian short-rate variance and Black expectation.
    B = quad(lambda u: math.exp(-a * u), 0, U - E)[0]
    variance = quad(lambda u: sigma * sigma * math.exp(-2 * a * u), 0, E)[0] * B * B
    sd = math.sqrt(variance)
    pe = math.exp(-f0 * E)
    pu = math.exp(-f0 * U)
    F = pu / pe
    d1 = (math.log(F / K) + 0.5 * variance) / sd
    d2 = d1 - sd
    exact = K * pe * norm.cdf(-d2) - pu * norm.cdf(-d1)
    samples = row["discounts"] * np.maximum(K - bond, 0)
    se = samples.std(ddof=1) / math.sqrt(samples.size)
    assert abs(samples.mean() - exact) < 5 * se + 2e-5


def test_time_and_maturity_discretization_have_distinct_error_controls():
    m = model()
    sigma = 0.02

    def vol(t, T):
        return np.array([sigma])

    # Zero Brownian increments expose the left-time Euler drift quadrature.
    errors = []
    for n in [8, 32, 128]:
        f = 0.04
        for t in np.arange(n) / n:
            f = m.hjm_forward_step([f], t, [2.0], 1 / n, [0.0], vol)[0]
        exact = 0.04 + sigma * sigma * (2 - 0.5)
        errors.append(abs(f - exact))
    assert errors[1] == pytest.approx(errors[0] / 4, rel=1e-9)
    assert errors[2] == pytest.approx(errors[1] / 4, rel=1e-9)
    with pytest.raises(ValueError):
        m.finite_forward_sde(1, 2, 2, vol)
    with pytest.raises(ValueError):
        m.hjm_forward_step([0.04], 1, [2], -1, [0], vol)


def test_same_short_rate_two_histories_have_different_future_drift_noise():
    def vol(t, T):
        return np.array([0.01 * (1 + 0.2 * (T - t))])

    m = model()
    a = m.hjm_history_noise(1, [0, 0.5], [[0.1], [0]], vol)
    b = m.hjm_history_noise(1, [0, 0.5], [[0], [0.1 * 0.012 / 0.011]], vol)
    assert a["rate_noise"] == pytest.approx(b["rate_noise"], abs=1e-14)
    assert a["maturity_slope_noise"] == pytest.approx(0.0002, abs=1e-12)
    assert abs(a["maturity_slope_noise"] - b["maturity_slope_noise"]) > 1e-5
