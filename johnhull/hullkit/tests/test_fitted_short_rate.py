"""§32.1 Ho–Lee/HW fit and independent Gaussian kernels; BK/BDT constraints."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._fitted_short_rate")


def logdf(t):
    return -0.025 * t - 0.0015 * t * t - 0.004 * (-math.expm1(-0.4 * t)) / 0.4


def forward(t):
    return 0.025 + 0.003 * t + 0.004 * math.exp(-0.4 * t)


def derivative(t):
    return 0.003 - 0.0016 * math.exp(-0.4 * t)


@pytest.mark.parametrize("a", [0, 1e-9, 0.1, 0.3])
def test_ho_lee_hw_fitted_curve_conditional_moments_and_pde_match_independent_integrals(a):
    m = model()
    sigma = 0.012
    t = 0.75
    T = 5
    r = -0.01
    horizon = T - t

    def loading(u):
        return u if a == 0 else -math.expm1(-a * u) / a

    def theta(s):
        return (
            derivative(s)
            + a * forward(s)
            + sigma * sigma * (s if a == 0 else -math.expm1(-2 * a * s) / (2 * a))
        )

    assert m.gaussian_curve_theta(t, a, sigma, forward, derivative) == pytest.approx(
        theta(t), abs=1e-14
    )
    meanI = loading(horizon) * r + quad(lambda s: loading(T - s) * theta(s), t, T, epsabs=1e-13)[0]
    variance = sigma * sigma * quad(lambda s: loading(s) ** 2, 0, horizon, epsabs=1e-13)[0]
    independent = math.exp(-meanI + variance / 2)
    price = m.gaussian_fitted_bond(t, T, r, a, sigma, logdf, forward)
    assert price == pytest.approx(independent, rel=2e-12)
    assert m.gaussian_fitted_bond(0, T, forward(0), a, sigma, logdf, forward) == pytest.approx(
        math.exp(logdf(T)), rel=1e-13
    )
    row = m.gaussian_fitted_moments(t, T, r, a, sigma, logdf, forward)
    assert row["mean_integral"] == pytest.approx(meanI, abs=1e-12)
    assert row["variance_integral"] == pytest.approx(variance, abs=1e-13)
    rng = np.random.default_rng(3212026)
    samples = np.exp(-meanI + math.sqrt(variance) * rng.standard_normal(131072))
    se = samples.std(ddof=1) / math.sqrt(samples.size)
    assert abs(samples.mean() - price) < 5 * se
    step = 1e-4

    def value(time, rate):
        return m.gaussian_fitted_bond(time, T, rate, a, sigma, logdf, forward)

    vt = (value(t + step, r) - value(t - step, r)) / (2 * step)
    vr = (value(t, r + step) - value(t, r - step)) / (2 * step)
    vrr = (value(t, r + step) - 2 * price + value(t, r - step)) / step**2
    residual = vt + (theta(t) - a * r) * vr + 0.5 * sigma * sigma * vrr - r * price
    assert abs(residual) < 1e-9


def test_ho_lee_limit_and_negative_initial_forward_curve():
    m = model()
    t = 1
    T = 4
    r = -0.01
    s = 0.01

    def negative_logdf(u):
        return 0.01 * u

    def negative_forward(u):
        return -0.01

    p = m.gaussian_fitted_bond(t, T, r, 0, s, negative_logdf, negative_forward)
    assert p > 1
    assert m.gaussian_fitted_bond(
        t, T, r, 1e-9, s, negative_logdf, negative_forward
    ) == pytest.approx(p, abs=1e-10)
    assert m.gaussian_fitted_bond(
        T, T, r, 0.1, s, negative_logdf, negative_forward
    ) == pytest.approx(1)


@pytest.mark.parametrize(
    "a,theta,sigma", [(0.2, -0.6, 0.25), (0, 0.01, 0.25), (-0.2, -0.6, 0.25), (0.2, -0.6, 0)]
)
def test_log_rate_step_matches_independent_log_ou_integral_and_lognormal_mc(a, theta, sigma):
    m = model()
    r = 0.04
    dt = 0.5
    B = dt if a == 0 else -math.expm1(-a * dt) / a
    variance = sigma * sigma * (dt if a == 0 else -math.expm1(-2 * a * dt) / (2 * a))
    mean = math.log(r) * math.exp(-a * dt) + theta * B
    expectation = math.exp(mean + 0.5 * variance)
    integral = quad(
        lambda z: (
            math.exp(mean + math.sqrt(variance) * z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        ),
        -11,
        11,
        epsabs=1e-13,
    )[0]
    assert expectation == pytest.approx(integral, rel=1e-12)
    z = np.random.default_rng(3212026).standard_normal(131072)
    samples = m.log_rate_step(r, theta, a, sigma, dt, z)
    assert np.all(samples > 0)
    se = samples.std(ddof=1) / math.sqrt(samples.size)
    assert abs(samples.mean() - expectation) <= 5 * se + 1e-13


def test_bdt_vol_derivative_constraint_and_bk_independent_mean_reversion():
    m = model()
    assert m.bdt_mean_reversion(0.2, 0) == pytest.approx(0)
    assert m.bdt_mean_reversion(0.2, -0.04) == pytest.approx(0.2)
    assert m.bdt_mean_reversion(0.2, 0.04) == pytest.approx(-0.2)
    for a in [0, 0.1, 0.5]:
        assert m.log_rate_step(0.04, -0.6, a, 0.2, 0.5, 0) > 0
    with pytest.raises(ValueError):
        m.bdt_mean_reversion(0, 0.01)
