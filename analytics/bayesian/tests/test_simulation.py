"""Data generators, Monte Carlo helpers, utils, and distribution grids."""

import numpy as np
import pytest
from bayes_textbook import distributions, simulation, utils
from bayes_textbook.conjugacy import BetaBinomial
from scipy import stats


def test_ab_test_data_reproducible():
    a = simulation.make_ab_test_data(seed=42)
    b = simulation.make_ab_test_data(seed=42)
    assert a.equals(b)
    assert set(a["variant"]) == {"A", "B"}
    assert (a["conversions"] <= a["visitors"]).all()


def test_prob_a_beats_b_symmetric_is_half():
    post = BetaBinomial(50, 50)
    p = simulation.prob_a_beats_b(post, post, n=200_000, seed=0)
    assert p == pytest.approx(0.5, abs=0.01)


def test_prob_a_beats_b_orders_correctly():
    strong = BetaBinomial(60, 40)
    weak = BetaBinomial(40, 60)
    assert simulation.prob_a_beats_b(strong, weak, n=50_000) > 0.95


def test_store_conversions_shape_and_bounds():
    df = simulation.make_store_conversions(n_stores=8, seed=1)
    assert len(df) == 8
    assert (df["conversions"] <= df["visits"]).all()
    assert df["true_rate"].between(0, 1).all()


def test_wine_ratings_long_format():
    df = simulation.make_wine_ratings(n_wines=5, seed=2)
    assert set(df.columns) == {"wine", "rating", "true_quality"}
    assert df["wine"].nunique() == 5
    assert df["rating"].between(1, 10).all()


def test_write_sample_csvs(tmp_path):
    paths = simulation.write_sample_csvs(tmp_path)
    assert all(p.exists() for p in paths)
    assert {p.name for p in paths} == {"ab_test.csv", "store_conversions.csv"}


def test_grid_pdf_integrates_to_one():
    x, y = distributions.grid_pdf(stats.norm(2, 3), n=2000, tail=1e-5)
    assert np.trapezoid(y, x) == pytest.approx(1.0, abs=1e-3)


def test_grid_pmf_sums_to_one():
    _k, p = distributions.grid_pmf(stats.poisson(4), tail=1e-9)
    assert p.sum() == pytest.approx(1.0, abs=1e-6)


def test_simplex_projection_corners():
    x, y = distributions.simplex_to_xy(np.eye(3))
    np.testing.assert_allclose(x, [0.0, 1.0, 0.5])
    np.testing.assert_allclose(y, [0.0, 0.0, np.sqrt(3) / 2])


def test_credible_interval_and_hdi_on_normal():
    rng = utils.rng(0)
    samples = rng.normal(0, 1, 200_000)
    lo, hi = utils.credible_interval(samples, 0.95)
    assert lo == pytest.approx(-1.96, abs=0.03)
    assert hi == pytest.approx(1.96, abs=0.03)
    hlo, hhi = utils.hdi(samples, 0.95)
    # For a symmetric unimodal distribution, HDI ~ equal-tailed CI.
    assert hlo == pytest.approx(lo, abs=0.05)
    assert hhi == pytest.approx(hi, abs=0.05)


def test_hdi_narrower_for_skewed():
    rng = utils.rng(1)
    samples = rng.gamma(2.0, 1.0, 200_000)
    lo, hi = utils.credible_interval(samples, 0.9)
    hlo, hhi = utils.hdi(samples, 0.9)
    assert (hhi - hlo) <= (hi - lo)


def test_summarize_posterior_keys():
    s = utils.summarize_posterior(np.arange(100.0), level=0.9)
    assert {"mean", "sd", "ci_90", "hdi_90"} <= set(s)
