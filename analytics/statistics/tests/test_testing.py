"""Hypothesis tests: their size, their power, and what multiplicity does."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import simulation as sim
from stats_textbook import testing as tst

# Measured reference: Bonferroni rejects 1, BH rejects 2 at alpha = 0.05.
PVALS = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216])


def test_one_sample_t_test_matches_scipy():
    rng = np.random.default_rng(0)
    x = rng.normal(0.4, 1.0, 30)
    got = tst.t_test(x, mu0=0.0)
    ref = stats.ttest_1samp(x, 0.0)
    assert abs(got.statistic - ref.statistic) < 1e-12
    assert abs(got.pvalue - ref.pvalue) < 1e-12
    assert got.df == 29


def test_two_sample_welch_test_matches_scipy():
    rng = np.random.default_rng(1)
    x, y = rng.normal(0, 1, 25), rng.normal(0.8, 2.0, 40)
    got = tst.two_sample_t_test(x, y, equal_var=False)
    ref = stats.ttest_ind(x, y, equal_var=False)
    assert abs(got.statistic - ref.statistic) < 1e-12
    assert abs(got.pvalue - ref.pvalue) < 1e-12


def test_the_test_rejects_at_exactly_alpha_under_the_null():
    r = sim.rejection_rate(
        lambda n, rng: rng.normal(0.0, 1.0, n),
        lambda s: tst.t_test(s).pvalue,
        alpha=0.05,
        n=20,
        n_reps=4000,
        seed=2,
    )
    lo, hi = r.ci95()
    assert lo <= 0.05 <= hi, f"size {r.estimate} with CI {(lo, hi)}"


def test_analytic_power_matches_simulated_power():
    """The non-central t formula must agree with actually running the test."""
    effect, n = 0.6, 25
    analytic = tst.power_t_test(effect, n, alpha=0.05)
    simulated = sim.rejection_rate(
        lambda m, rng: rng.normal(effect, 1.0, m),
        lambda s: tst.t_test(s).pvalue,
        alpha=0.05,
        n=n,
        n_reps=4000,
        seed=3,
    )
    lo, hi = simulated.ci95()
    assert lo <= analytic <= hi, f"analytic {analytic:.4f} vs simulated {(lo, hi)}"


def test_power_rises_with_effect_and_sample_size():
    assert tst.power_t_test(0.2, 25) < tst.power_t_test(0.8, 25)
    assert tst.power_t_test(0.5, 10) < tst.power_t_test(0.5, 100)
    assert abs(tst.power_t_test(0.0, 50) - 0.05) < 1e-9, "at zero effect power is alpha"


def test_required_n_reaches_the_requested_power():
    # Measured: 34 for effect 0.5, 199 for 0.2, 15 for 0.8.
    n = tst.required_n(effect=0.5, alpha=0.05, power=0.8)
    assert n == 34, f"got {n}"
    assert tst.power_t_test(0.5, n) >= 0.8
    assert tst.power_t_test(0.5, n - 1) < 0.8, "must be the smallest such n"


def test_power_stays_finite_where_scipys_nct_overflows():
    """nct returns nan at large non-centrality; power there is 1, not nan."""
    for n in [500, 3000, 5000]:
        p = tst.power_t_test(0.5, n)
        assert np.isfinite(p) and p > 0.999, f"n={n} gave {p}"


def test_bonferroni_and_bh_match_statsmodels():
    from statsmodels.stats.multitest import multipletests

    for method, fn in [("bonferroni", tst.bonferroni), ("fdr_bh", tst.benjamini_hochberg)]:
        ref = multipletests(PVALS, alpha=0.05, method=method)[0]
        np.testing.assert_array_equal(fn(PVALS, alpha=0.05), ref)


def test_bh_rejects_more_than_bonferroni():
    assert tst.benjamini_hochberg(PVALS).sum() > tst.bonferroni(PVALS).sum()


def test_uncorrected_testing_produces_false_positives_in_bulk():
    """The p-hacking demonstration NB08 is built on."""
    rng = np.random.default_rng(4)
    n_tests = 200
    pvals = np.array([tst.t_test(rng.normal(0, 1, 30)).pvalue for _ in range(n_tests)])
    raw = (pvals < 0.05).sum()
    assert raw >= 5, "about 5% of pure noise should look significant"
    assert tst.bonferroni(pvals).sum() == 0
    assert tst.benjamini_hochberg(pvals).sum() == 0


def test_false_discovery_proportion_counts_only_true_nulls():
    rejected = np.array([True, True, True, False])
    is_null = np.array([True, False, False, True])
    assert abs(tst.false_discovery_proportion(rejected, is_null) - 1 / 3) < 1e-12
    assert tst.false_discovery_proportion(np.zeros(4, bool), is_null) == 0.0


def test_bh_controls_the_false_discovery_rate():
    """Average FDP over many experiments must stay under alpha."""
    rng = np.random.default_rng(5)
    fdps = []
    for _ in range(200):
        # 180 nulls, 20 real effects.
        null_p = rng.uniform(0, 1, 180)
        alt_p = np.array([tst.t_test(rng.normal(1.0, 1.0, 20)).pvalue for _ in range(20)])
        pvals = np.concatenate([null_p, alt_p])
        is_null = np.concatenate([np.ones(180, bool), np.zeros(20, bool)])
        fdps.append(tst.false_discovery_proportion(tst.benjamini_hochberg(pvals, 0.1), is_null))
    assert np.mean(fdps) <= 0.10 + 0.02, f"mean FDP {np.mean(fdps):.4f}"


def test_multiple_testing_rejects_bad_alpha():
    with pytest.raises(ValueError, match="alpha"):
        tst.benjamini_hochberg(PVALS, alpha=1.5)
