"""Interval estimation, and what "95%" is actually a claim about."""

import numpy as np
import pytest
from stats_textbook import intervals as iv
from stats_textbook import simulation as sim


def test_interval_reports_containment_and_width():
    i = iv.Interval(lo=-1.0, hi=2.0)
    assert i.contains(0.0) and not i.contains(3.0)
    assert abs(i.width() - 3.0) < 1e-12


def test_t_interval_matches_the_textbook_formula():
    from scipy import stats

    x = np.array([2.1, 1.8, 2.6, 2.0, 2.4, 1.9])
    got = iv.t_interval(x)
    half = stats.t.ppf(0.975, x.size - 1) * x.std(ddof=1) / np.sqrt(x.size)
    assert abs(got.lo - (x.mean() - half)) < 1e-12
    assert abs(got.hi - (x.mean() + half)) < 1e-12


def test_wald_interval_uses_the_normal_quantile():
    got = iv.wald_interval(estimate=10.0, se=2.0, level=0.95)
    assert abs(got.width() - 2 * 1.959963984540054 * 2.0) < 1e-9


def test_t_interval_covers_at_its_nominal_rate():
    def sampler(n, rng):
        return rng.normal(0.0, 1.0, n)

    r = sim.coverage_probability(
        sampler, lambda s: tuple(iv.t_interval(s)), truth=0.0, n=12, n_reps=4000, seed=1
    )
    lo, hi = r.ci95()
    assert lo <= 0.95 <= hi, f"nominal 95% outside the Monte-Carlo CI {(lo, hi)}"


def test_bootstrap_percentile_interval_covers_a_median():
    """The median has no simple standard error -- this is what bootstrap is for."""

    def sampler(n, rng):
        return rng.exponential(1.0, n)

    truth = float(np.log(2.0))  # median of Exponential(1)

    def interval(s):
        return tuple(iv.bootstrap_interval(s, np.median, method="percentile", n_boot=400, seed=0))

    r = sim.coverage_probability(sampler, interval, truth=truth, n=60, n_reps=400, seed=5)
    assert 0.88 <= r.estimate <= 0.99, f"coverage {r.estimate}"


def test_bca_beats_percentile_on_a_skewed_statistic():
    """BCa corrects for bias and skew; on a variance of skewed data it should
    not be worse than the plain percentile interval."""

    def sampler(n, rng):
        return rng.exponential(1.0, n)

    truth = 1.0  # variance of Exponential(1)
    out = {}
    for method in ["percentile", "bca"]:

        def interval(s, _m=method):
            return tuple(
                iv.bootstrap_interval(s, lambda a: a.var(ddof=1), method=_m, n_boot=400, seed=0)
            )

        out[method] = sim.coverage_probability(
            sampler, interval, truth=truth, n=40, n_reps=300, seed=6
        ).estimate
    assert out["bca"] >= out["percentile"] - 0.02, out


def test_bootstrap_rejects_an_unknown_method():
    with pytest.raises(ValueError, match="method"):
        iv.bootstrap_interval(np.arange(10.0), np.mean, method="studentized")


def test_bootstrap_is_deterministic():
    x = np.arange(1.0, 21.0)
    a = iv.bootstrap_interval(x, np.mean, n_boot=200, seed=7)
    b = iv.bootstrap_interval(x, np.mean, n_boot=200, seed=7)
    assert a == b


def test_permutation_test_finds_a_real_shift_and_not_a_fake_one():
    rng = np.random.default_rng(8)
    same_a, same_b = rng.normal(0, 1, 60), rng.normal(0, 1, 60)
    diff_a, diff_b = rng.normal(0, 1, 60), rng.normal(1.2, 1, 60)
    assert iv.permutation_test(same_a, same_b, n_perm=2000, seed=0) > 0.1
    assert iv.permutation_test(diff_a, diff_b, n_perm=2000, seed=0) < 0.01


def test_permutation_pvalue_is_uniform_under_the_null():
    """A valid p-value rejects at exactly alpha when nothing is going on."""

    def sampler(n, rng):
        return rng.normal(0.0, 1.0, 2 * n)

    def pvalue(s):
        half = s.size // 2
        return iv.permutation_test(s[:half], s[half:], n_perm=400, seed=0)

    r = sim.rejection_rate(sampler, pvalue, alpha=0.1, n=25, n_reps=600, seed=9)
    lo, hi = r.ci95()
    assert lo <= 0.10 <= hi, f"nominal alpha outside {(lo, hi)}"
