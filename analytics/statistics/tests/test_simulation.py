"""The Monte-Carlo harness that every 'we checked it by simulation' claim uses."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import simulation as sim


def normal_sampler(n, rng):
    return rng.normal(0.0, 1.0, n)


def t_interval(sample):
    """The textbook 95% t interval for a normal mean."""
    n = sample.size
    half = stats.t.ppf(0.975, n - 1) * sample.std(ddof=1) / np.sqrt(n)
    return float(sample.mean() - half), float(sample.mean() + half)


def broken_interval(sample):
    """Uses the normal quantile and divides by n instead of sqrt(n)."""
    half = 1.96 * sample.std(ddof=1) / sample.size
    return float(sample.mean() - half), float(sample.mean() + half)


def t_test_pvalue(sample):
    return float(stats.ttest_1samp(sample, 0.0).pvalue)


def test_monte_carlo_result_reports_a_sensible_interval():
    r = sim.MonteCarloResult(estimate=0.95, se=0.01, n_reps=500)
    lo, hi = r.ci95()
    assert lo < 0.95 < hi
    assert abs((hi - lo) - 2 * 1.96 * 0.01) < 1e-12


def test_sampling_distribution_shape_and_determinism():
    a = sim.sampling_distribution(np.mean, normal_sampler, n=25, n_reps=400, seed=7)
    b = sim.sampling_distribution(np.mean, normal_sampler, n=25, n_reps=400, seed=7)
    assert a.shape == (400,)
    np.testing.assert_array_equal(a, b)
    # The sample mean of 25 standard normals has sd 0.2.
    assert abs(a.std(ddof=1) - 0.2) < 0.03


def test_coverage_of_the_t_interval_is_the_nominal_95_percent():
    r = sim.coverage_probability(normal_sampler, t_interval, truth=0.0, n=12, n_reps=4000, seed=1)
    assert r.n_reps == 4000
    lo, hi = r.ci95()
    assert lo <= 0.95 <= hi, f"nominal 95% fell outside the Monte-Carlo CI {(lo, hi)}"


def test_coverage_detects_a_broken_interval():
    r = sim.coverage_probability(
        normal_sampler, broken_interval, truth=0.0, n=12, n_reps=4000, seed=1
    )
    # Dividing by n instead of sqrt(n) makes the interval far too narrow.
    assert r.estimate < 0.6


def test_rejection_rate_under_the_null_is_alpha():
    r = sim.rejection_rate(normal_sampler, t_test_pvalue, alpha=0.05, n=20, n_reps=4000, seed=2)
    lo, hi = r.ci95()
    assert lo <= 0.05 <= hi, f"nominal alpha fell outside the Monte-Carlo CI {(lo, hi)}"


def test_rejection_rate_rises_with_a_real_effect():
    def shifted(n, rng):
        return rng.normal(0.8, 1.0, n)

    r = sim.rejection_rate(shifted, t_test_pvalue, alpha=0.05, n=20, n_reps=2000, seed=3)
    # Power at n=20, effect 0.8 sd is well above alpha.
    assert r.estimate > 0.8


def test_rejection_rate_rejects_bad_alpha():
    with pytest.raises(ValueError, match="alpha"):
        sim.rejection_rate(normal_sampler, t_test_pvalue, alpha=1.5, n=10, n_reps=10)
