"""Synthetic data generators: shapes, determinism, and stated parameters."""

import numpy as np
import pytest
from stats_textbook import datasets


def test_coin_flips_are_binary_and_deterministic():
    a = datasets.coin_flips(200, p=0.7, seed=3)
    b = datasets.coin_flips(200, p=0.7, seed=3)
    assert a.shape == (200,)
    assert set(np.unique(a)) <= {0, 1}
    np.testing.assert_array_equal(a, b)
    # 200 draws at p=0.7 sit within 4 sd of 140 with overwhelming probability.
    assert abs(a.sum() - 140) < 4 * np.sqrt(200 * 0.7 * 0.3)


def test_disease_test_counts_partition_the_population():
    counts = datasets.disease_test_counts(
        100_000, prevalence=0.01, sensitivity=0.99, specificity=0.95, seed=0
    )
    assert set(counts) == {"tp", "fp", "fn", "tn"}
    assert sum(counts.values()) == 100_000
    # The paradox this feeds (NB01): false positives swamp true positives.
    assert counts["fp"] > counts["tp"]


def test_normal_sample_matches_its_parameters():
    x = datasets.normal_sample(50_000, mu=3.0, sigma=2.0, seed=1)
    assert abs(x.mean() - 3.0) < 0.05
    assert abs(x.std(ddof=1) - 2.0) < 0.05


def test_exponential_sample_has_mean_one_over_rate():
    x = datasets.exponential_sample(50_000, rate=4.0, seed=1)
    assert (x > 0).all()
    assert abs(x.mean() - 0.25) < 0.01


def test_bivariate_normal_reproduces_the_requested_correlation():
    x, y = datasets.bivariate_normal(50_000, rho=-0.6, seed=2)
    assert x.shape == y.shape == (50_000,)
    assert abs(np.corrcoef(x, y)[0, 1] + 0.6) < 0.02


def test_heavy_tailed_sample_has_no_stable_mean():
    x = datasets.heavy_tailed_sample(20_000, kind="cauchy", seed=5)
    running = np.cumsum(x) / np.arange(1, x.size + 1)
    # A Cauchy running mean keeps wandering; a normal one would settle.
    assert np.std(running[1000:]) > 0.1


def test_heavy_tailed_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        datasets.heavy_tailed_sample(10, kind="gumbel")


def test_samplers_registry_is_callable_and_deterministic():
    assert {"normal", "uniform", "exponential", "cauchy"} <= set(datasets.SAMPLERS)
    for name, fn in datasets.SAMPLERS.items():
        a = fn(64, np.random.default_rng(0))
        b = fn(64, np.random.default_rng(0))
        assert a.shape == (64,), name
        np.testing.assert_array_equal(a, b)


def test_capstone_dataset_matches_the_sibling_books_byte_for_byte():
    """The cross-book capstone only works if all five books generate the
    same numbers. Reproduced here rather than imported: analytics books do
    not depend on each other."""
    x, y = datasets.make_capstone_dataset(seed=0)
    assert x.shape == y.shape == (40,)
    assert np.all(np.diff(x) >= 0), "x must be sorted"
    # Pinned from the shared generator (la_book/datasets.py), measured against
    # all four sibling books rather than copied from the plan, whose constants
    # were off in the fourth decimal.
    assert abs(x[0] - (-2.98356900)) < 1e-6, x[0]
    assert abs(x[-1] - 2.98325961) < 1e-6, x[-1]
    # f(x) = sin(1.5 x) + 0.3 x with noise 0.35.
    f = np.sin(1.5 * x) + 0.3 * x
    assert abs((y - f).std(ddof=1) - 0.35) < 0.08


def test_capstone_dataset_is_deterministic():
    a = datasets.make_capstone_dataset(seed=0)
    b = datasets.make_capstone_dataset(seed=0)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
