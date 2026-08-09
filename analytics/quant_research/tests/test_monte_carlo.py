import numpy as np
import pytest
from quant_textbook import (
    antithetic_variates,
    brownian_bridge,
    control_variate,
    estimate_confidence_interval,
    estimate_expectation,
    importance_sampling,
    quadratic_variation,
    simulate_brownian_motion,
    simulate_gbm_euler,
    simulate_gbm_exact,
    simulate_paths,
    spawn_generators,
)


def test_spawned_streams_are_reproducible_and_not_duplicated() -> None:
    first = spawn_generators(81, 4)
    second = spawn_generators(81, 4)
    first_draws = np.vstack([generator.standard_normal(12) for generator in first])
    second_draws = np.vstack([generator.standard_normal(12) for generator in second])

    np.testing.assert_array_equal(first_draws, second_draws)
    assert np.unique(first_draws, axis=0).shape[0] == 4


def test_generic_path_simulator_separates_step_from_payoff() -> None:
    times = np.array([0.0, 0.25, 1.0])

    def deterministic_step(state, time, time_step, rng):
        del time, rng
        return state + 2.0 * time_step

    paths = simulate_paths(
        3.0,
        times,
        n_paths=5,
        step=deterministic_step,
        rng=np.random.default_rng(2),
    )
    assert paths.shape == (5, 3)
    np.testing.assert_allclose(paths, np.tile([3.0, 3.5, 5.0], (5, 1)))
    np.testing.assert_allclose(np.maximum(paths[:, -1] - 4.0, 0.0), 1.0)


def test_expectation_and_confidence_interval_report_standard_error() -> None:
    samples = np.array([1.0, 2.0, 3.0, 4.0])
    result = estimate_expectation(samples)
    interval = estimate_confidence_interval(samples)

    assert result.estimate == pytest.approx(2.5)
    assert result.sample_standard_deviation == pytest.approx(np.std(samples, ddof=1))
    assert result.standard_error == pytest.approx(np.std(samples, ddof=1) / 2.0)
    assert result.confidence_interval == interval
    assert interval.lower < result.estimate < interval.upper

    constant = estimate_expectation(np.ones(10))
    assert constant.standard_error == 0.0
    assert constant.confidence_interval.lower == 1.0
    assert constant.confidence_interval.upper == 1.0


def test_brownian_moments_and_quadratic_variation_match_theory() -> None:
    times = np.linspace(0.0, 1.5, 601)
    paths = simulate_brownian_motion(
        times,
        12_000,
        rng=np.random.default_rng(92),
    )
    terminal = paths[:, -1]
    qv = quadratic_variation(paths)

    assert terminal.mean() == pytest.approx(0.0, abs=0.035)
    assert terminal.var(ddof=1) == pytest.approx(1.5, rel=0.035)
    assert qv.mean() == pytest.approx(1.5, rel=0.01)
    assert qv.std(ddof=1) < 0.1


def test_exact_gbm_agrees_with_analytic_mean() -> None:
    initial_price = 100.0
    drift = 0.04
    volatility = 0.25
    horizon = 1.2
    paths = simulate_gbm_exact(
        initial_price,
        drift,
        volatility,
        [0.0, horizon],
        120_000,
        rng=np.random.default_rng(103),
    )
    terminal = paths[:, -1]
    expected = initial_price * np.exp(drift * horizon)
    standard_error = terminal.std(ddof=1) / np.sqrt(terminal.size)
    assert abs(terminal.mean() - expected) < 4.0 * standard_error


def test_euler_strong_error_and_analytic_weak_bias_shrink() -> None:
    initial_price = 100.0
    drift = 0.08
    volatility = 0.3
    n_paths = 50_000
    errors = []
    for n_steps in (4, 128):
        times = np.linspace(0.0, 1.0, n_steps + 1)
        seed = 111 + n_steps
        exact = simulate_gbm_exact(
            initial_price,
            drift,
            volatility,
            times,
            n_paths,
            rng=np.random.default_rng(seed),
        )
        euler = simulate_gbm_euler(
            initial_price,
            drift,
            volatility,
            times,
            n_paths,
            rng=np.random.default_rng(seed),
        )
        errors.append(np.mean(np.abs(euler[:, -1] - exact[:, -1])))
    assert errors[1] < 0.3 * errors[0]

    exact_mean = initial_price * np.exp(drift)
    coarse_mean = initial_price * (1.0 + drift / 4.0) ** 4
    fine_mean = initial_price * (1.0 + drift / 128.0) ** 128
    assert abs(fine_mean - exact_mean) < abs(coarse_mean - exact_mean) / 20.0


def test_antithetic_and_control_variate_reduce_call_payoff_variance() -> None:
    n_pairs = 60_000
    initial_price = 100.0
    rate = 0.03
    volatility = 0.25
    strike = 105.0
    discount = np.exp(-rate)
    paired = antithetic_variates(
        n_pairs,
        1,
        rng=np.random.default_rng(122),
    ).ravel()
    terminal = initial_price * np.exp(rate - 0.5 * volatility**2 + volatility * paired)
    payoffs = discount * np.maximum(terminal - strike, 0.0)
    pair_means = 0.5 * (payoffs[:n_pairs] + payoffs[n_pairs:])
    plain_variance = float(payoffs[:n_pairs].var(ddof=1))
    assert pair_means.var(ddof=1) < plain_variance

    controls = discount * terminal[:n_pairs]
    result = control_variate(
        payoffs[:n_pairs],
        controls,
        known_control_mean=initial_price,
    )
    assert result.coefficient > 0.0
    assert result.variance_reduction_ratio > 2.0
    assert result.adjusted_variance < result.raw_variance


def test_importance_sampling_matches_normal_tail_with_lower_error() -> None:
    threshold = 4.0
    count = 120_000
    result = importance_sampling(
        threshold,
        count,
        proposal_mean=4.0,
        rng=np.random.default_rng(133),
    )
    analytic = NormalTail.sf(threshold)
    direct_standard_error = np.sqrt(analytic * (1.0 - analytic) / count)

    assert abs(result.estimate - analytic) < 5.0 * result.standard_error
    assert result.standard_error < direct_standard_error / 10.0
    assert 0.0 < result.effective_sample_size <= count
    assert result.weight_mean > 0.0
    assert result.max_weight >= result.weight_mean
    assert result.nonzero_contributions > count // 3
    assert 0.0 < result.max_contribution_share < 0.01
    assert result.log_weight_range > 0.0


def test_importance_sampling_preserves_extreme_tail_standard_error() -> None:
    result = importance_sampling(
        38.0,
        100_000,
        proposal_mean=38.0,
        rng=np.random.default_rng(1),
    )

    assert result.estimate > 0.0
    assert result.standard_error > 0.0
    assert result.confidence_interval.upper > result.confidence_interval.lower
    assert result.nonzero_contributions > 40_000
    assert result.weight_coefficient_of_variation_squared > 0.0
    assert np.isfinite(result.log_weight_variance)
    assert result.weight_variance_underflow


def test_importance_sampling_rejects_zero_event_contributions() -> None:
    with pytest.raises(RuntimeError, match="no event contributions"):
        importance_sampling(
            8.0,
            100_000,
            proposal_mean=0.0,
            rng=np.random.default_rng(1),
        )


class NormalTail:
    @staticmethod
    def sf(value: float) -> float:
        from math import erfc, sqrt

        return 0.5 * erfc(value / sqrt(2.0))


def test_brownian_bridge_fixes_endpoints_and_matches_midpoint_moments() -> None:
    times = np.linspace(0.0, 2.0, 101)
    paths = brownian_bridge(
        times,
        start=-0.5,
        end=1.0,
        n_paths=20_000,
        rng=np.random.default_rng(144),
    )
    midpoint = paths[:, 50]
    np.testing.assert_array_equal(paths[:, 0], np.full(paths.shape[0], -0.5))
    np.testing.assert_array_equal(paths[:, -1], np.full(paths.shape[0], 1.0))
    assert midpoint.mean() == pytest.approx(0.25, abs=0.02)
    assert midpoint.var(ddof=1) == pytest.approx(0.5, rel=0.035)


@pytest.mark.parametrize(
    ("function", "message"),
    [
        (lambda: estimate_expectation([1.0]), "at least 2"),
        (
            lambda: simulate_brownian_motion([0.0, 0.0], 2, rng=np.random.default_rng(1)),
            "strictly increasing",
        ),
        (
            lambda: control_variate([1.0, 2.0], [1.0, 1.0], 1.0),
            "positive sample variance",
        ),
        (
            lambda: antithetic_variates(2, rng=2),  # type: ignore[arg-type]
            "Generator",
        ),
        (
            lambda: simulate_brownian_motion(
                [0.0, 1.0],
                3,
                rng=np.random.default_rng(1),
                antithetic=True,
            ),
            "even n_paths",
        ),
    ],
)
def test_invalid_inputs_are_rejected(function, message) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        function()
