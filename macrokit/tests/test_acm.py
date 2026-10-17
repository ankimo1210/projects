import numpy as np
import pytest

from macrokit.termstructure import acm, synthetic, var


def test_pricing_recursion_matches_monte_carlo():
    rng = np.random.default_rng(5)
    mu = np.array([0.0001, 0.0])
    phi = np.array([[0.97, 0.02], [0.0, 0.9]])
    chol = np.diag([0.005, 0.004])
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
    # ~5 Monte Carlo standard errors; the convexity term is ~7e-3
    assert a[12] + b[12] @ x0 == pytest.approx(mc, abs=1.5e-3)


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
    # By Jensen's inequality, convexity puts the zero-risk-price yield below the expected short rate.
    assert gap.mean() < 0


def test_acm_recovers_the_affine_curve_on_a_long_sample():
    syn = synthetic.affine_dgp(5000, np.random.default_rng(7))
    fit = acm.fit_acm(syn.panel, k=3)
    assert np.abs(fit.fitted_yield(120) - syn.panel.column(120)).mean() < 0.03
    # The RMSE bound is a fixed-draw pin for seed 7. Over seeds 0-29 at T=5000 the median RMSE is
    # 0.168 and 9 of 30 seeds exceed 0.2: the error is mostly the level error from the sample mean
    # of the phi=0.99 factor, so a different draw can fail without a bug. The correlation check
    # below is seed-robust (minimum 0.9973 over 30 seeds).
    rmse = np.sqrt(((fit.expected(120) - syn.expected_pct) ** 2).mean())
    assert rmse < 0.2
    assert np.corrcoef(fit.expected(120), syn.expected_pct)[0, 1] > 0.99


def test_decompose_uses_the_observed_yield():
    syn = synthetic.affine_dgp(600, np.random.default_rng(8))
    fit = acm.fit_acm(syn.panel, k=3)
    dec = acm.decompose_acm(syn.panel, fit)
    np.testing.assert_array_equal(dec.yield_pct, syn.panel.column(120))
    assert dec.model == "acm"


def test_kilian_moves_an_ar1_estimate_toward_the_truth():
    rng = np.random.default_rng(11)
    raw, corrected = [], []
    for _ in range(100):
        x = np.zeros((200, 1))
        for t in range(1, 200):
            x[t] = 0.98 * x[t - 1] + rng.normal()
        fit = var.fit_var1(x)
        raw.append(fit.phi[0, 0])
        corrected.append(acm.kilian_correct(x, fit, 300, rng).phi[0, 0])
    assert abs(np.mean(corrected) - 0.98) < 0.5 * abs(np.mean(raw) - 0.98)


def test_kilian_keeps_the_sample_mean_on_the_stationary_branch():
    rng = np.random.default_rng(21)
    true_phi = np.array([[0.93, 0.15], [0.0, 0.85]])  # asymmetric: no transpose can hide
    x = np.zeros((180, 2))
    for t in range(1, 180):
        x[t] = np.array([0.2, 0.1]) + true_phi @ x[t - 1] + rng.normal(size=2)
    fit = var.fit_var1(x)
    out = acm.kilian_correct(x, fit, 200, rng)
    assert out.shrink > 0.0
    assert not np.allclose(out.phi, fit.phi)
    np.testing.assert_allclose(out.mu, (np.eye(2) - out.phi) @ x.mean(axis=0))
    assert not np.allclose(out.mu, fit.mu)


def test_shrink_stops_at_the_first_stationary_step():
    phi, shrink = acm.shrink_to_stationary(np.array([[0.99]]), np.array([[-0.045]]))
    assert shrink == pytest.approx(0.22)
    assert phi[0, 0] < 1.0


def test_shrink_returns_the_estimate_when_no_step_is_stationary():
    phi, shrink = acm.shrink_to_stationary(np.array([[1.01]]), np.array([[-0.01]]))
    assert shrink == 0.0
    assert phi[0, 0] == 1.01


def test_kilian_leaves_a_non_stationary_estimate_alone():
    x = np.cumsum(np.ones((50, 1)), axis=0)
    fit = var.Var1(mu=np.array([1.0]), phi=np.array([[1.01]]), resid=np.zeros((49, 1)))
    out = acm.kilian_correct(x, fit, 10, np.random.default_rng(0))
    assert out.shrink == 0.0
    np.testing.assert_array_equal(out.phi, fit.phi)
    np.testing.assert_array_equal(out.mu, fit.mu)


def test_bootstrap_expected_is_centred_on_the_point_estimate():
    syn = synthetic.affine_dgp(400, np.random.default_rng(12))
    fit = acm.fit_acm(syn.panel, k=3)
    draws = acm.bootstrap_expected(fit, 120, 200, np.random.default_rng(13))
    assert draws.shape == (200, 400)
    # Pins this fixed draw. Baseline gap 0.030 and std 0.33; no residuals std 4e-16; x3 std 0.97.
    last = draws[:, -1]
    point = fit.expected(120)[-1]
    assert abs(np.median(last) - point) < 0.1
    assert 0.1 < last.std() < 0.6
    assert np.quantile(last, 0.05) < point < np.quantile(last, 0.95)


def test_bias_corrected_bootstrap_draws_from_the_corrected_dgp():
    syn = synthetic.affine_dgp(400, np.random.default_rng(12))
    fit = acm.fit_acm(syn.panel, k=3)
    corrected = acm.bootstrap_expected(fit, 120, 20, np.random.default_rng(14), correction_boot=20)
    plain = acm.bootstrap_expected(fit, 120, 20, np.random.default_rng(14))
    assert corrected.shape == (20, 400)
    assert np.isfinite(corrected).all()
    assert not np.allclose(corrected, plain)
    kc = acm.kilian_correct(fit.factors, fit.var, 20, np.random.default_rng(15))
    assert abs(np.median(corrected[:, -1]) - fit.expected(120, kc.mu, kc.phi)[-1]) < 0.5
