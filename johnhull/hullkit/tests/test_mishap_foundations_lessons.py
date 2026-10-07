"""GE Ch37 probability/diversification pins, separate from historical incident amounts."""

import itertools
import math

import numpy as np
import pytest
from hullkit import _mishap_foundations as m


def test_source_streak_and_independent_binomial_enumeration():
    result = m.streak_success(16, 4, 0.5)
    assert result["individual_probability"] == pytest.approx(1 / 16, abs=1e-14)
    assert result["expected_successes"] == pytest.approx(1, abs=1e-14)
    successful_paths = sum(all(path) for path in itertools.product([False, True], repeat=4))
    p = successful_paths / 2**4
    count_law = [math.comb(16, k) * p**k * (1 - p) ** (16 - k) for k in range(17)]
    assert result["expected_successes"] == pytest.approx(
        sum(k * p for k, p in enumerate(count_law)), abs=1e-14
    )
    assert result["any_success_probability"] == pytest.approx(sum(count_law[1:]), abs=1e-14)
    assert result["any_success_probability"] == pytest.approx(0.64392587, abs=5e-9)
    assert result["any_success_probability"] < 1
    rng = np.random.default_rng(370101)
    experiments = rng.random((40000, 16, 4)) < 0.5
    any_success = np.any(np.all(experiments, axis=2), axis=1)
    se = math.sqrt(
        result["any_success_probability"]
        * (1 - result["any_success_probability"])
        / len(experiments)
    )
    assert abs(any_success.mean() - result["any_success_probability"]) < 6 * se


def test_source_diversification_matrix_and_factor_mc():
    result = m.equal_correlation_portfolio(20, 0.1, 0.3, 0.2)
    assert result["expected_return"] == pytest.approx(0.1, abs=1e-14)
    assert result["volatility"] * 100 == pytest.approx(14.7, rel=0, abs=0.05)
    covariance = 0.3**2 * (0.8 * np.eye(20) + 0.2 * np.ones((20, 20)))
    weights = np.full(20, 1 / 20)
    assert result["variance"] == pytest.approx(weights @ covariance @ weights, abs=1e-14)
    rng = np.random.default_rng(370102)
    count = 80000
    observations = 0.1 + 0.3 * (
        math.sqrt(0.2) * rng.standard_normal((count, 1))
        + math.sqrt(0.8) * rng.standard_normal((count, 20))
    )
    portfolio = observations.mean(axis=1)
    assert abs(portfolio.mean() - 0.1) < 6 * math.sqrt(result["variance"] / count)
    variance_se = result["variance"] * math.sqrt(2 / (count - 1))
    assert abs(portfolio.var(ddof=1) - result["variance"]) < 6 * variance_se


def test_probability_boundaries_and_correlation_feasibility():
    assert m.streak_success(0, 4, 0.5)["any_success_probability"] == pytest.approx(0, abs=1e-14)
    assert m.streak_success(3, 0, 0)["any_success_probability"] == pytest.approx(1, abs=1e-14)
    assert m.streak_success(3, 2, 1)["expected_successes"] == pytest.approx(3, abs=1e-14)
    assert m.streak_success(3, 2, 0)["expected_successes"] == pytest.approx(0, abs=1e-14)
    assert m.equal_correlation_portfolio(1, 0.1, 0.3, 0)["volatility"] == pytest.approx(
        0.3, abs=1e-14
    )
    assert m.equal_correlation_portfolio(4, 0.1, 0.3, -1 / 3)["variance"] == pytest.approx(
        0, abs=1e-14
    )
    assert m.equal_correlation_portfolio(20, 0.1, 0.3, 1)["volatility"] == pytest.approx(
        0.3, abs=1e-14
    )
    with pytest.raises(ValueError):
        m.streak_success(3, -1, 0.5)
    with pytest.raises(ValueError):
        m.streak_success(3, 4, 1.1)
    with pytest.raises(ValueError):
        m.equal_correlation_portfolio(20, 0.1, 0.3, -0.1)
