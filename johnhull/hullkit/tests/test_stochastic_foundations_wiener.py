"""Hull GE 14.2: normal examples, coherent Brownian refinement and variation."""

import math

import numpy as np
import pytest
from hullkit import _stochastic_foundations as stochastic
from scipy.integrate import quad
from scipy.stats import norm


def test_hull_standard_wiener_variances_and_example_14_1():
    for t, sd in [(2, math.sqrt(2)), (0.5, math.sqrt(0.5)), (0.25, 0.5), (3, math.sqrt(3))]:
        mean, variance, std = stochastic.wiener_moments(0, 0, 1, t)
        assert [mean, variance, std] == pytest.approx([0, t, sd], abs=1e-12)
    assert stochastic.wiener_moments(25, 0, 1, 1)[2] == pytest.approx(1, abs=1e-12)
    assert stochastic.wiener_moments(25, 0, 1, 5)[2] == pytest.approx(2.236, abs=0.0005)


def test_hull_cash_balance_example_14_2_and_independent_normal_integrals():
    for t, printed_mean, printed_sd in [(1, 70, 30), (0.5, 60, 21.21)]:
        mean, variance, sd = stochastic.wiener_moments(50, 20, 30, t)
        assert mean == pytest.approx(printed_mean, abs=1e-12)
        assert sd == pytest.approx(printed_sd, abs=0.005)
        independent_mean = quad(
            lambda z, t=t: (50 + 20 * t + 30 * math.sqrt(t) * z) * norm.pdf(z), -10, 10
        )[0]
        independent_variance = quad(
            lambda z, t=t: (30 * math.sqrt(t) * z) ** 2 * norm.pdf(z), -10, 10
        )[0]
        assert [mean, variance] == pytest.approx([independent_mean, independent_variance], abs=1e-8)


def test_generalized_wiener_mc_moments_with_standard_errors():
    rng = np.random.default_rng(1402)
    n = 30000
    times = np.linspace(0, 1, 11)
    paths = stochastic.wiener_paths(50, 20, 30, times, rng.standard_normal((n, 10)))
    for index, t in [(5, 0.5), (10, 1)]:
        target_mean, target_variance, _ = stochastic.wiener_moments(50, 20, 30, t)
        sample = paths[:, index]
        assert abs(sample.mean() - target_mean) < 6 * sample.std(ddof=1) / math.sqrt(n)
        assert abs(sample.var(ddof=1) - target_variance) < 6 * target_variance * math.sqrt(
            2 / (n - 1)
        )
    # Figure 14.2 uses drift .3 and diffusion 1.5, with supplied common noise.
    figure = stochastic.wiener_paths(0, 0.3, 1.5, times, np.zeros((1, 10)))
    assert figure[0] == pytest.approx(0.3 * times, abs=1e-12)


def test_bridge_refinement_preserves_coarse_path_and_has_correct_conditional_variance():
    rng = np.random.default_rng(141)
    n = 30000
    times = np.array([0, 0.25, 1.0])
    coarse = stochastic.wiener_paths(0, 0, 1, times, rng.standard_normal((n, 2)))
    fine_times, fine = stochastic.brownian_bridge_refine(times, coarse, rng.standard_normal((n, 2)))
    assert fine_times == pytest.approx([0, 0.125, 0.25, 0.625, 1], abs=1e-12)
    assert np.allclose(fine[:, ::2], coarse, atol=1e-12, rtol=0)
    residual = fine[:, 1::2] - (coarse[:, :-1] + coarse[:, 1:]) / 2
    for k, target_var in enumerate([0.25 / 4, 0.75 / 4]):
        assert abs(residual[:, k].mean()) < 6 * math.sqrt(target_var / n)
        assert abs(residual[:, k].var(ddof=1) - target_var) < 6 * target_var * math.sqrt(
            2 / (n - 1)
        )
    increments = np.diff(fine, axis=1)
    independent_covariance = np.diag(np.diff(fine_times))
    observed = np.cov(increments, rowvar=False)
    se = np.sqrt(
        (
            np.outer(np.diag(independent_covariance), np.diag(independent_covariance))
            + independent_covariance**2
        )
        / (n - 1)
    )
    assert np.all(np.abs(observed - independent_covariance) < 6 * se)


def test_total_variation_expectation_matches_independent_absolute_normal_integral_and_mc():
    absolute_normal = quad(lambda z: abs(z) * norm.pdf(z), -10, 10)[0]
    expected = []
    rng = np.random.default_rng(14011)
    for steps in [4, 16, 64]:
        target = stochastic.brownian_path_length_mean(1, steps)
        assert target == pytest.approx(steps * absolute_normal / math.sqrt(steps), abs=1e-10)
        values = np.abs(rng.standard_normal((12000, steps)) / math.sqrt(steps)).sum(axis=1)
        assert abs(values.mean() - target) < 6 * values.std(ddof=1) / math.sqrt(len(values))
        expected.append(target)
    assert expected[1] == pytest.approx(2 * expected[0], abs=1e-12)
    assert expected[2] == pytest.approx(2 * expected[1], abs=1e-12)


def test_negative_time_or_nonincreasing_grid_is_rejected():
    with pytest.raises(ValueError):
        stochastic.wiener_moments(0, 0, 1, -1)
    with pytest.raises(ValueError):
        stochastic.wiener_paths(0, 0, 1, [0, 0.5, 0.5], [[0, 0]])
