"""Hull §25.9 cumulative PD and correlation extremes, independent count/latent references."""

import math

import numpy as np
import pytest
from hullkit import _credit_portfolio_extensions as e
from scipy.stats import norm


def test_source_100_names_two_percent_five_year_pd_four_printed_numbers():
    distribution = e.default_count_distribution(100, 0.02, 0)
    exact = np.array([math.comb(100, k) * 0.02**k * 0.98 ** (100 - k) for k in range(101)])
    assert distribution == pytest.approx(exact, abs=1e-14)
    assert distribution[1:].sum() * 100 == pytest.approx(86.74, abs=0.005)
    assert distribution[10:].sum() * 100 == pytest.approx(0.0034, abs=0.00005)
    perfect = e.default_count_distribution(100, 0.02, 1)
    assert perfect[[0, 100]] == pytest.approx([0.98, 0.02])
    assert perfect[1:100].sum() == pytest.approx(0)


def test_intermediate_correlation_against_direct_normal_latent_count_mc():
    rng = np.random.default_rng(259)
    latent = math.sqrt(0.4) * rng.normal(size=(140_000, 1)) + math.sqrt(0.6) * rng.normal(
        size=(140_000, 20)
    )
    count = (latent < norm.ppf(0.1)).sum(axis=1)
    distribution = e.default_count_distribution(20, 0.1, 0.4, nodes=120)
    for k in (1, 3, 8):
        indicator = (count >= k).astype(float)
        assert abs(indicator.mean() - distribution[k:].sum()) <= 6 * indicator.std(
            ddof=1
        ) / math.sqrt(count.size)


def test_expected_loss_conserved_but_equity_senior_redistributed_with_correlation():
    results = []
    for rho in (0, 0.3, 0.6, 1):
        pmf = e.default_count_distribution(100, 0.02, rho, nodes=200)
        loss = e.loss_waterfall(np.arange(101) / 100, 1, [0, 0.05, 0.2, 1])["allocated_loss"]
        expected = pmf @ loss
        assert expected.sum() == pytest.approx(0.02, abs=2e-12)
        results.append(expected)
    assert results[-1][0] < results[0][0]
    assert results[-1][-1] > results[0][-1]
    assert results[-1] / np.array([0.05, 0.15, 0.8]) == pytest.approx([0.02] * 3)
    # Recovery .4 leaves the top 40% unhit even when all names default.
    pmf = e.default_count_distribution(100, 0.02, 1)
    layer = e.loss_waterfall(0.6 * np.arange(101) / 100, 1, [0, 0.6, 1])["allocated_loss"]
    assert (pmf @ layer)[1] == pytest.approx(0)


def test_invalid_probability_correlation_and_name_count():
    for args in [(0, 0.1, 0.3), (10, -0.1, 0.3), (10, 0.1, 1.01)]:
        with pytest.raises(ValueError):
            e.default_count_distribution(*args)


@pytest.mark.parametrize("rho", [0.9, 0.99])
def test_review_r6_high_correlation_count_tail_against_split_adaptive_binomial(rho):
    from scipy.integrate import quad
    from scipy.stats import binom

    threshold = norm.ppf(0.02)
    center = threshold / math.sqrt(rho)
    width = math.sqrt(1 - rho) / math.sqrt(rho)
    anchors = [v for v in center + np.array([-8, -4, -1, 0, 1, 4, 8]) * width if -12 < v < 12]
    exact = quad(
        lambda f: (
            norm.pdf(f)
            * binom.sf(9, 100, norm.cdf((threshold - math.sqrt(rho) * f) / math.sqrt(1 - rho)))
        ),
        -12,
        12,
        points=anchors,
        epsabs=1e-11,
        epsrel=1e-11,
    )[0]
    pmf = e.default_count_distribution(100, 0.02, rho)
    assert pmf[10:].sum() == pytest.approx(exact, abs=2e-10)
    assert np.arange(101) @ pmf == pytest.approx(2, abs=2e-9)
