"""Conjugate updates checked against formulas and Monte Carlo."""

import numpy as np
import pytest
from bayes_textbook.conjugacy import (
    BetaBinomial,
    DirichletMultinomial,
    GammaPoisson,
    NormalNormal,
)
from scipy import stats


def test_beta_binomial_update_params():
    post = BetaBinomial(2, 2).update(successes=34, failures=16)
    assert post.alpha == 36 and post.beta == 18
    assert post.mean == pytest.approx(36 / 54)


def test_beta_binomial_map_and_ci():
    post = BetaBinomial(2, 2).update(7, 3)
    assert post.map == pytest.approx((9 - 1) / (14 - 2))
    lo, hi = post.credible_interval(0.95)
    assert lo < post.mean < hi
    # Equal-tailed: 2.5% mass below lo.
    assert post.dist.cdf(lo) == pytest.approx(0.025, abs=1e-9)


def test_beta_binomial_map_requires_interior_mode():
    with pytest.raises(ValueError):
        _ = BetaBinomial(1.0, 5.0).map


def test_beta_binomial_posterior_predictive_matches_mc():
    post = BetaBinomial(3, 5)
    _k, pmf = post.posterior_predictive(n_new=10)
    assert pmf.sum() == pytest.approx(1.0, abs=1e-9)
    # Monte Carlo: draw theta then binomial; compare P(X = 3).
    rng = np.random.default_rng(0)
    thetas = post.dist.rvs(200_000, random_state=rng)
    xs = rng.binomial(10, thetas)
    assert (xs == 3).mean() == pytest.approx(pmf[3], abs=0.005)


def test_gamma_poisson_update_and_mean():
    post = GammaPoisson(2.0, 1.0).update(total_count=30, n_obs=10)
    assert post.alpha == 32 and post.beta == 11
    assert post.mean == pytest.approx(32 / 11)


def test_gamma_poisson_predictive_is_negative_binomial():
    post = GammaPoisson(4.0, 2.0)
    _k, pmf = post.posterior_predictive(k_max=40)
    rng = np.random.default_rng(1)
    lam = post.dist.rvs(200_000, random_state=rng)
    xs = rng.poisson(lam)
    for kk in [0, 2, 5]:
        assert (xs == kk).mean() == pytest.approx(pmf[kk], abs=0.005)


def test_normal_normal_update_formula():
    prior = NormalNormal(mu0=0.0, tau0=2.0, sigma=1.0)
    data = np.array([1.0, 2.0, 3.0])
    post = prior.update(data)
    prec = 1 / 4 + 3 / 1
    assert post.tau0 == pytest.approx(np.sqrt(1 / prec))
    assert post.mu0 == pytest.approx((1 / prec) * (0 + data.sum()))


def test_normal_normal_data_dominates_with_n():
    prior = NormalNormal(mu0=-5.0, tau0=1.0, sigma=2.0)
    rng = np.random.default_rng(2)
    data = rng.normal(3.0, 2.0, 5000)
    post = prior.update(data)
    assert abs(post.mu0 - data.mean()) < 0.05  # prior forgotten
    assert post.tau0 < 0.05


def test_normal_normal_predictive_wider_than_posterior():
    post = NormalNormal(1.0, 0.3, sigma=1.5)
    pred = post.posterior_predictive()
    assert pred.std() == pytest.approx(np.sqrt(1.5**2 + 0.3**2))
    assert pred.std() > post.tau0


def test_dirichlet_multinomial_update_and_mean():
    post = DirichletMultinomial((1.0, 1.0, 1.0)).update([10, 5, 0])
    assert tuple(post.alpha) == (11.0, 6.0, 1.0)
    np.testing.assert_allclose(post.mean, [11 / 18, 6 / 18, 1 / 18])
    assert post.mean.sum() == pytest.approx(1.0)
    samples = post.sample(5000, seed=0)
    np.testing.assert_allclose(samples.mean(axis=0), post.mean, atol=0.02)


def test_posterior_concentrates_like_sqrt_n():
    # Doubling the data (same rate) shrinks the posterior sd by ~sqrt(2).
    sd_small = BetaBinomial(1, 1).update(30, 70).dist.std()
    sd_big = BetaBinomial(1, 1).update(60, 140).dist.std()
    assert sd_small / sd_big == pytest.approx(np.sqrt(2), rel=0.05)


def test_update_is_associative_in_data():
    # Updating with all data at once == sequential updates (Bayes consistency).
    once = BetaBinomial(2, 3).update(10, 5)
    seq = BetaBinomial(2, 3).update(4, 2).update(6, 3)
    assert once == seq
