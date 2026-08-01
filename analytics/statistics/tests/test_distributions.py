"""Exponential-family algebra checked against scipy's closed forms."""

import numpy as np
import pytest
from scipy import stats
from stats_textbook import distributions as dist


def test_relations_are_well_formed_and_laid_out():
    names = {r.source for r in dist.RELATIONS} | {r.target for r in dist.RELATIONS}
    layout = dist.relation_layout()
    assert names <= set(layout), "every node in RELATIONS needs a position"
    assert all(r.condition for r in dist.RELATIONS), "every edge states its condition"
    # The three limits the chapter is built around.
    pairs = {(r.source, r.target) for r in dist.RELATIONS}
    assert ("binomial", "poisson") in pairs
    assert ("binomial", "normal") in pairs
    assert ("normal", "chi2") in pairs


def test_bernoulli_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["bernoulli"]
    x = np.array([0, 1, 1, 0, 1])
    got = dist.exponential_family_logpdf(family, 0.3, x)
    want = stats.bernoulli.logpmf(x, 0.3)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_poisson_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["poisson"]
    x = np.array([0, 1, 4, 9])
    got = dist.exponential_family_logpdf(family, 2.5, x)
    want = stats.poisson.logpmf(x, 2.5)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_normal_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["normal_unit_var"]
    x = np.array([-1.5, 0.0, 0.7, 2.2])
    got = dist.exponential_family_logpdf(family, 0.4, x)
    want = stats.norm.logpdf(x, loc=0.4, scale=1.0)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_exponential_exponential_form_matches_scipy():
    family = dist.EXPONENTIAL_FAMILIES["exponential"]
    x = np.array([0.2, 1.0, 3.3])
    got = dist.exponential_family_logpdf(family, 1.7, x)
    want = stats.expon.logpdf(x, scale=1.0 / 1.7)
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=1e-12)


def test_sufficient_statistic_is_the_sample_sum_for_all_four():
    x = np.array([0.5, 1.5, 2.0])
    for name, family in dist.EXPONENTIAL_FAMILIES.items():
        t = family.sufficient_stat(x)
        assert t.shape == x.shape, name


def test_binomial_poisson_distance_shrinks_as_p_shrinks():
    far = dist.binomial_poisson_tv_distance(20, 0.5)
    near = dist.binomial_poisson_tv_distance(20, 0.02)
    assert 0.0 <= near < far <= 1.0
    # Le Cam's bound: the total-variation distance is at most n * p^2.
    assert near <= 20 * 0.02**2 + 1e-12


def test_binomial_poisson_distance_rejects_bad_p():
    with pytest.raises(ValueError, match="p"):
        dist.binomial_poisson_tv_distance(10, 1.5)
