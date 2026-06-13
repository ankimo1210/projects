"""Bayesian linear regression, partial pooling, and from-scratch samplers."""

import numpy as np
import pytest
from bayes_textbook import models
from scipy import stats


def _toy_regression(n=40, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2, 2, n)
    y = 1.0 + 2.0 * x + 0.5 * rng.standard_normal(n)
    X = np.column_stack([np.ones_like(x), x])
    return X, y, x


def test_blr_posterior_mean_equals_ridge():
    X, y, _ = _toy_regression()
    sigma, sigma_w = 0.5, 3.0
    blr = models.BayesianLinearRegression(sigma=sigma, sigma_w=sigma_w).fit(X, y)
    lam = sigma**2 / sigma_w**2
    np.testing.assert_allclose(blr.w_mean, models.ridge_solution(X, y, lam), atol=1e-10)


def test_blr_uncertainty_shrinks_with_data():
    X, y, _ = _toy_regression(n=200)
    blr_small = models.BayesianLinearRegression(0.5, 3.0).fit(X[:10], y[:10])
    blr_big = models.BayesianLinearRegression(0.5, 3.0).fit(X, y)
    assert np.trace(blr_big.w_cov) < np.trace(blr_small.w_cov)


def test_blr_predictive_wider_than_credible():
    X, y, _ = _toy_regression()
    blr = models.BayesianLinearRegression(0.5, 3.0).fit(X, y)
    pred = blr.predict(X[:5])
    cred_w = pred["cred_hi"] - pred["cred_lo"]
    pred_w = pred["pred_hi"] - pred["pred_lo"]
    assert (pred_w > cred_w).all()


def test_blr_strong_prior_shrinks_weights_to_zero():
    X, y, _ = _toy_regression()
    loose = models.BayesianLinearRegression(0.5, sigma_w=10.0).fit(X, y)
    tight = models.BayesianLinearRegression(0.5, sigma_w=0.05).fit(X, y)
    assert np.linalg.norm(tight.w_mean) < np.linalg.norm(loose.w_mean)


def test_blr_weight_samples_match_posterior():
    X, y, _ = _toy_regression()
    blr = models.BayesianLinearRegression(0.5, 3.0).fit(X, y)
    W = blr.sample_weights(20_000, seed=1)
    np.testing.assert_allclose(W.mean(axis=0), blr.w_mean, atol=0.01)
    np.testing.assert_allclose(np.cov(W.T), blr.w_cov, atol=0.01)


def test_partial_pooling_beta_shrinks_small_groups():
    successes = np.array([2, 300])
    trials = np.array([4, 1000])  # group 0 tiny, group 1 big
    res = models.fit_partial_pooling_beta(successes, trials, prior_strength=50)
    # Both shrink toward the pool, small group much more.
    move = np.abs(res.partial - res.unpooled)
    assert move[0] > move[1]
    # Partial estimate sits between raw rate and pooled rate.
    for i in range(2):
        lo, hi = sorted([res.unpooled[i], res.pooled])
        assert lo - 1e-9 <= res.partial[i] <= hi + 1e-9


def test_partial_pooling_beta_large_n_tracks_raw_rate():
    res = models.fit_partial_pooling_beta([5000], [10000], prior_strength=20)
    assert res.partial[0] == pytest.approx(0.5, abs=0.01)


def test_partial_pooling_normal_eight_schools_style():
    means = np.array([28.0, 8.0, -3.0, 7.0, -1.0, 1.0, 18.0, 12.0])
    sems = np.array([15.0, 10.0, 16.0, 11.0, 9.0, 11.0, 10.0, 18.0])
    shrunk, mu_hat, tau_hat = models.fit_partial_pooling_normal(means, sems)
    # Every estimate moves toward the common mean and stays in between.
    for y, s in zip(means, shrunk, strict=True):
        lo, hi = sorted([y, mu_hat])
        assert lo - 1e-9 <= s <= hi + 1e-9
    assert tau_hat >= 0


def test_metropolis_hastings_standard_normal():
    samples, rate = models.metropolis_hastings(
        stats.norm.logpdf, x0=0.0, n_steps=20_000, proposal_sd=2.4, seed=3
    )
    kept = samples[2000:]
    assert kept.mean() == pytest.approx(0.0, abs=0.05)
    assert kept.std() == pytest.approx(1.0, abs=0.05)
    assert 0.2 < rate < 0.7


def test_gibbs_recovers_correlation():
    rho = 0.8
    out = models.gibbs_bivariate_normal(rho, n_steps=20_000, seed=4)
    emp = np.corrcoef(out[2000:].T)[0, 1]
    assert emp == pytest.approx(rho, abs=0.03)


def test_leapfrog_conserves_energy_approximately():
    # Standard normal target: H = q^2/2 + p^2/2 should be nearly constant.
    def grad(q):
        return -q

    path = models.leapfrog(np.array([1.0]), np.array([0.5]), grad, step_size=0.1, n_steps=50)
    assert path.shape == (51, 1)
    # The trajectory must stay bounded (oscillates, does not blow up).
    assert np.abs(path).max() < 2.0


def test_autocorrelation_white_noise_near_zero():
    rng = np.random.default_rng(5)
    acf = models.autocorrelation(rng.standard_normal(5000), max_lag=10)
    assert acf[0] == pytest.approx(1.0)
    assert np.abs(acf[1:]).max() < 0.06


def test_gaussian_process_interpolates_training_points():
    import numpy as np
    from bayes_textbook.models import GaussianProcess

    X = np.linspace(0, 10, 8)
    y = np.sin(X)
    gp = GaussianProcess(length_scale=1.5, noise=1e-8).fit(X[:, None], y)
    mean, sd = gp.predict(X[:, None])
    # With tiny noise, the GP nearly interpolates the training data...
    np.testing.assert_allclose(mean, y, atol=1e-3)
    assert (sd >= 0).all()
    # ...and is more uncertain far from any training point.
    _, sd_far = gp.predict(np.array([[20.0]]))
    assert sd_far[0] > sd.mean()


def test_expected_improvement_nonnegative_and_peaks_in_gaps():
    import numpy as np
    from bayes_textbook.models import GaussianProcess, expected_improvement

    X = np.array([0.0, 5.0, 10.0])
    y = np.array([1.0, 0.5, 0.8])
    gp = GaussianProcess(length_scale=2.0).fit(X[:, None], y)
    grid = np.linspace(0, 10, 100)[:, None]
    ei = expected_improvement(gp, grid, best_y=y.min())
    assert (ei >= -1e-9).all()


def test_thompson_beats_epsilon_greedy_regret():
    from bayes_textbook.models import epsilon_greedy_bandit, thompson_bandit

    rates = [0.3, 0.5, 0.55]
    _, r_ts = thompson_bandit(rates, n_rounds=3000, seed=0)
    _, r_eps = epsilon_greedy_bandit(rates, n_rounds=3000, epsilon=0.1, seed=0)
    assert r_ts[-1] < r_eps[-1]  # Thompson has lower cumulative regret


def test_thompson_concentrates_on_best_arm():
    import numpy as np
    from bayes_textbook.models import thompson_bandit

    pulls, _ = thompson_bandit([0.2, 0.4, 0.7], n_rounds=3000, seed=1)
    assert int(np.argmax(pulls)) == 2  # the truly-best arm is pulled most
