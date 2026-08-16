"""The Bayesian side of NB11, implemented here so the book stays standalone."""

import numpy as np
import pytest
from stats_textbook import bridge
from stats_textbook import simulation as sim


def test_posterior_is_the_conjugate_beta():
    post = bridge.beta_binomial_posterior(8, 10, prior_a=1.0, prior_b=1.0)
    # Beta(1 + 8, 1 + 2)
    assert abs(post.args[0] - 9.0) < 1e-12
    assert abs(post.args[1] - 3.0) < 1e-12


def test_posterior_mean_is_a_weighted_average_of_prior_and_data():
    k, n, a, b = 7, 10, 20.0, 5.0
    got = bridge.posterior_mean(k, n, a, b)
    assert abs(got - (a + k) / (a + b + n)) < 1e-12
    # It sits between the prior mean and the MLE.
    prior_mean, mle = a / (a + b), k / n
    assert min(prior_mean, mle) <= got <= max(prior_mean, mle)


def test_prior_influence_vanishes_as_n_grows():
    """Measured: a strong Beta(20, 5) prior pulls the estimate 0.167 away
    from the MLE at n=5 and 0.0002 away at n=10000."""
    gaps = []
    for n in [5, 100, 10_000]:
        k = int(0.7 * n)
        gaps.append(abs(bridge.posterior_mean(k, n, 20.0, 5.0) - k / n))
    assert gaps[0] > 0.15
    assert gaps[-1] < 0.001
    assert gaps[0] > gaps[1] > gaps[2]


def test_credible_interval_stays_inside_the_unit_interval():
    """The headline contrast of NB11. A Wald interval does not have to."""
    ci = bridge.credible_interval(8, 10)
    assert 0.0 <= ci.lo < ci.hi <= 1.0

    from stats_textbook import intervals as iv

    p_hat = 0.8
    wald = iv.wald_interval(p_hat, np.sqrt(p_hat * (1 - p_hat) / 10))
    assert wald.hi > 1.0, "the Wald interval leaves the parameter space here"


def test_credible_interval_narrows_with_more_data():
    widths = [bridge.credible_interval(int(0.8 * n), n).width() for n in [10, 100, 1000]]
    assert widths[0] > widths[1] > widths[2]
    # 1/sqrt(n) shrinkage: ten times the data, about a third the width.
    assert 2.5 < widths[0] / widths[1] < 4.0


def test_credible_interval_has_decent_frequentist_coverage():
    """Measured: at p=0.1, n=20 the Jeffreys interval covers 0.957 where
    the Wald interval manages 0.881. The Bayesian answer wins on the
    frequentist's own criterion."""
    p, n = 0.1, 20

    def sampler(m, rng):
        return (rng.random(m) < p).astype(float)

    jeff = sim.coverage_probability(
        sampler,
        lambda s: tuple(bridge.credible_interval(int(s.sum()), s.size)),
        truth=p,
        n=n,
        n_reps=8000,
        seed=0,
    )
    assert jeff.estimate > 0.93, jeff.estimate


def test_bayes_factor_favours_the_alternative_when_data_is_extreme():
    weak = bridge.bayes_factor_proportion(6, 10, p0=0.5)
    strong = bridge.bayes_factor_proportion(90, 100, p0=0.5)
    assert weak < 1.5, "6 of 10 is not evidence"
    assert strong > 100, "90 of 100 is"


def test_bayes_factor_of_a_fair_looking_sample_favours_the_null():
    assert bridge.bayes_factor_proportion(50, 100, p0=0.5) < 1.0


def test_priors_registry_has_the_three_the_chapter_uses():
    assert set(bridge.PRIORS) == {"jeffreys", "uniform", "strong_high"}
    assert bridge.PRIORS["jeffreys"] == (0.5, 0.5)


def test_rejects_impossible_counts():
    with pytest.raises(ValueError, match="k"):
        bridge.credible_interval(11, 10)
