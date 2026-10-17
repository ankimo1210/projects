import numpy as np
import pytest

from macrokit.termstructure import acm, synthetic


def test_pricing_recursion_matches_monte_carlo():
    rng = np.random.default_rng(5)
    mu = np.array([0.0001, 0.0])
    phi = np.array([[0.97, 0.02], [0.0, 0.9]])
    chol = np.diag([0.0005, 0.0004])
    d0, d1 = 0.002, np.array([1.0, 1.0])
    x0 = np.array([0.001, -0.0005])
    a, b = acm.pricing_recursion(mu, phi, chol @ chol.T, 0.0, d0, d1, 12)
    paths = 200_000
    x = np.broadcast_to(x0, (paths, 2)).copy()
    discount = np.zeros(paths)
    for _ in range(12):
        discount += d0 + x @ d1
        x = mu + x @ phi.T + rng.standard_normal((paths, 2)) @ chol.T
    mc = np.log(np.exp(-discount).mean())
    assert a[12] + b[12] @ x0 == pytest.approx(mc, abs=2e-4)  # ~5 Monte Carlo standard errors


def test_without_risk_prices_the_premium_is_a_constant_convexity_term():
    syn = synthetic.affine_dgp(600, np.random.default_rng(6))
    fit = acm.fit_acm(syn.panel, k=3)
    neutral = acm.AcmFit(
        fit.dates,
        fit.factors,
        fit.var,
        np.zeros(3),
        np.zeros((3, 3)),
        fit.delta0,
        fit.delta1,
        fit.sigma2,
    )
    np.testing.assert_allclose(
        neutral.fitted_yield(120), neutral.fitted_yield(120, risk_neutral=True)
    )
    gap = neutral.fitted_yield(120, risk_neutral=True) - neutral.expected(120)
    assert gap.std() < 1e-10


def test_acm_recovers_the_affine_curve_on_a_long_sample():
    syn = synthetic.affine_dgp(5000, np.random.default_rng(7))
    fit = acm.fit_acm(syn.panel, k=3)
    assert np.abs(fit.fitted_yield(120) - syn.panel.column(120)).mean() < 0.03
    rmse = np.sqrt(((fit.expected(120) - syn.expected_pct) ** 2).mean())
    assert rmse < 0.2


def test_decompose_uses_the_observed_yield():
    syn = synthetic.affine_dgp(600, np.random.default_rng(8))
    fit = acm.fit_acm(syn.panel, k=3)
    dec = acm.decompose_acm(syn.panel, fit)
    np.testing.assert_array_equal(dec.yield_pct, syn.panel.column(120))
    assert dec.model == "acm"
