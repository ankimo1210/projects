"""Estimators, likelihood, and the two kinds of Fisher information."""

import numpy as np
import pytest
from stats_textbook import estimation as est


def test_bernoulli_mle_is_the_sample_proportion():
    x = np.array([1, 0, 1, 1, 0, 1, 1, 0])
    r = est.mle("bernoulli", x)
    assert r.n == 8
    assert abs(r.estimate - x.mean()) < 1e-9


def test_poisson_mle_is_the_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.poisson(3.5, 500)
    assert abs(est.mle("poisson", x).estimate - x.mean()) < 1e-9


def test_normal_mle_is_the_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(1.2, 1.0, 500)
    assert abs(est.mle("normal_unit_var", x).estimate - x.mean()) < 1e-9


def test_exponential_mle_is_the_reciprocal_sample_mean():
    rng = np.random.default_rng(0)
    x = rng.exponential(1 / 2.5, 500)
    assert abs(est.mle("exponential", x).estimate - 1.0 / x.mean()) < 1e-9


def test_mle_maximises_the_log_likelihood():
    rng = np.random.default_rng(1)
    x = rng.poisson(4.0, 200)
    hat = est.mle("poisson", x).estimate
    best = est.log_likelihood("poisson", hat, x)
    for theta in [hat * 0.8, hat * 0.9, hat * 1.1, hat * 1.25]:
        assert est.log_likelihood("poisson", theta, x) < best


def test_expected_fisher_information_matches_the_closed_forms():
    # Bernoulli: n / (p(1-p)); Poisson: n / lambda.
    assert abs(est.expected_fisher_information("bernoulli", 0.3, 80) - 80 / 0.21) < 1e-9
    assert abs(est.expected_fisher_information("poisson", 2.5, 50) - 20.0) < 1e-9
    # Normal with unit variance: n.
    assert abs(est.expected_fisher_information("normal_unit_var", 1.7, 40) - 40.0) < 1e-9


def test_observed_and_expected_information_agree_at_the_mle_and_not_at_the_truth():
    """The chapter's point: which theta you evaluate at matters."""
    rng = np.random.default_rng(1)
    lam, n = 2.5, 50
    x = rng.poisson(lam, n)
    hat = est.mle("poisson", x).estimate

    def ll(theta):
        return est.log_likelihood("poisson", theta, x)

    at_mle = est.observed_information(ll, hat)
    assert abs(at_mle - est.expected_fisher_information("poisson", hat, n)) / at_mle < 1e-4
    # At the true parameter the two part company (the sample mean is not lambda).
    at_truth = est.observed_information(ll, lam)
    assert abs(at_truth - est.expected_fisher_information("poisson", lam, n)) > 1.0


def test_cramer_rao_bound_is_attained_by_the_mle_of_a_poisson_mean():
    """For an exponential family the MLE's asymptotic variance is the bound."""
    from stats_textbook import simulation as sim

    lam, n = 3.0, 200

    def sampler(m, rng):
        return rng.poisson(lam, m).astype(float)

    hats = sim.sampling_distribution(
        lambda s: est.mle("poisson", s).estimate, sampler, n=n, n_reps=4000, seed=2
    )
    bound = est.cramer_rao_bound("poisson", lam, n)
    assert abs(hats.var() / bound - 1.0) < 0.06, f"var {hats.var():.5f} vs bound {bound:.5f}"


def test_standard_error_uses_the_information_at_the_mle():
    rng = np.random.default_rng(3)
    x = rng.poisson(4.0, 250)
    r = est.mle("poisson", x)
    assert abs(r.se - np.sqrt(r.estimate / 250)) < 1e-9


def test_method_of_moments_agrees_with_the_mle_for_these_families():
    rng = np.random.default_rng(4)
    x = rng.poisson(3.0, 400)
    assert abs(est.method_of_moments("poisson", x) - est.mle("poisson", x).estimate) < 1e-9


def test_unknown_family_is_rejected():
    with pytest.raises(KeyError, match="cauchy"):
        est.mle("cauchy", np.array([1.0, 2.0]))
