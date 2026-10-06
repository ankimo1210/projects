"""Hull §22.6: fixed-seed MC, source ranks, and analytical quantiles."""

import numpy as np
import pytest
from hullkit import _market_risk as m
from scipy.stats import norm


def call_value(s, maturity=0.5):
    d1 = (np.log(s / 100) + (0.02 + 0.2**2 / 2) * maturity) / (0.2 * np.sqrt(maturity))
    return s * norm.cdf(d1) - 100 * np.exp(-0.02 * maturity) * norm.cdf(
        d1 - 0.2 * np.sqrt(maturity)
    )


def test_source_5000_sample_tail_ranks():
    for confidence, rank in [(0.99, 50), (0.95, 250)]:
        result = m.empirical_risk(-np.arange(5000), confidence)
        assert result["tail_rank"] == rank
        assert result["var"] == 5000 - rank


def test_multivariate_full_revaluation_matches_normal_quantile_with_six_se():
    spots = np.array([120, 30])
    shares = np.array([1000, 20000])
    cov = np.array([[0.02**2, 0.3 * 0.02 * 0.01], [0.3 * 0.02 * 0.01, 0.01**2]])
    result = m.simulation_risk(spots, cov, lambda s: s @ shares, samples=150000, seed=226)
    variance = sum(
        spots[i] * shares[i] * spots[j] * shares[j] * cov[i, j] for i in range(2) for j in range(2)
    )
    sigma = np.sqrt(variance)
    reference = sigma * norm.ppf(0.99)
    se = m.quantile_standard_error(150000, 0.99, norm.pdf(norm.ppf(0.99)) / sigma)
    assert result["risk"]["var"] == pytest.approx(reference, abs=6 * se)
    assert np.cov(result["changes"], rowvar=False) == pytest.approx(cov, rel=0.03)


def test_call_full_revaluation_monotone_quantile_and_gamma_direction():
    z = np.random.default_rng(225).normal(size=(160000, 1))
    s, daily = 100, 0.01
    result = m.simulation_risk([s], [[daily**2]], lambda spots: call_value(spots[:, 0]), normals=z)
    q = norm.ppf(0.01)
    cutoff = s * (1 + daily * q)
    exact = call_value(s) - call_value(cutoff)
    d1 = (np.log(cutoff / 100) + (0.02 + 0.2**2 / 2) * 0.5) / (0.2 * np.sqrt(0.5))
    density = norm.pdf(q) / (s * daily * norm.cdf(d1))
    se = m.quantile_standard_error(z.shape[0], 0.99, density)
    assert result["risk"]["var"] == pytest.approx(exact, abs=6 * se)
    delta = norm.cdf((0.02 + 0.2**2 / 2) * 0.5 / (0.2 * np.sqrt(0.5)))
    delta_var = delta * s * daily * norm.ppf(0.99)
    assert exact < delta_var  # positive gamma, with theta excluded
    short = call_value(s * (1 + daily * norm.ppf(0.99))) - call_value(s)
    assert short > delta_var


def test_full_and_partial_share_shocks_and_exact_quadratic_book():
    z = np.random.default_rng(8).normal(size=(5000, 2))
    s = np.array([2, 3])
    a = np.array([4, 2])
    beta = np.array([[0.5, 0.3], [0.3, -0.1]])

    def book(spots):
        x = spots / s - 1
        return (
            7
            + 4 * x[:, 0]
            + 2 * x[:, 1]
            + 0.5 * x[:, 0] ** 2
            + 0.6 * x[:, 0] * x[:, 1]
            - 0.1 * x[:, 1] ** 2
        )

    result = m.simulation_risk(
        s, [[0.01, 0.005], [0.005, 0.02]], book, normals=z, linear=a, beta=beta
    )
    assert result["pnl"] == pytest.approx(result["partial_pnl"], abs=2e-14)
    assert result["risk"]["var"] == pytest.approx(result["partial_risk"]["var"])


def test_n_day_callback_uses_actual_maturity_and_is_not_sqrt_scaling():
    z = np.linspace(-3, 3, 5000)[:, None]  # deterministic paired scenarios

    def book(spots):
        return call_value(spots[:, 0], 0.1)

    one = m.simulation_risk(
        [100],
        [[0.02**2]],
        book,
        normals=z,
        future_book=lambda spots: call_value(spots[:, 0], 0.1 - 1 / 252),
    )
    ten = m.simulation_risk(
        [100],
        [[0.02**2]],
        book,
        normals=z,
        horizon=10,
        future_book=lambda spots: call_value(spots[:, 0], 0.1 - 10 / 252),
    )
    assert ten["risk"]["var"] != pytest.approx(one["risk"]["var"] * np.sqrt(10), rel=0.01)
    assert ten["spots"][:, 0] == pytest.approx(100 * (1 + 0.02 * np.sqrt(10) * z[:, 0]))


def test_semidefinite_shocks_and_invalid_quantile_density():
    result = m.simulation_risk(
        [1, 1], [[0.01, 0.01], [0.01, 0.01]], lambda s: s[:, 0] - s[:, 1], samples=500, seed=6
    )
    assert result["pnl"] == pytest.approx(np.zeros(500), abs=1e-14)
    with pytest.raises(ValueError):
        m.quantile_standard_error(1000, 0.99, 0)
