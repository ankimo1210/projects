import numpy as np
import pytest
from quant_textbook import (
    analyze_markov_chain,
    diagnose_optional_stopping,
    first_exit_times,
    random_walk_optional_stopping,
    simulate_markov_chain,
    stationary_distribution,
    validate_transition_matrix,
)


def test_stationary_distribution_and_chain_structure() -> None:
    transition = np.array([[0.9, 0.1], [0.2, 0.8]])
    result = analyze_markov_chain(transition)

    assert result.is_irreducible
    assert result.is_aperiodic
    assert result.period == 1
    assert result.stationary.is_unique
    np.testing.assert_allclose(result.stationary.probabilities, [2.0 / 3.0, 1.0 / 3.0])
    assert result.stationary.residual_norm < 1e-14
    assert result.stationary.spectral_gap == pytest.approx(0.3)


def test_periodic_and_reducible_chains_are_diagnosed() -> None:
    periodic = analyze_markov_chain([[0.0, 1.0], [1.0, 0.0]])
    reducible = analyze_markov_chain(np.eye(2))

    assert periodic.is_irreducible
    assert not periodic.is_aperiodic
    assert periodic.period == 2
    assert periodic.stationary.spectral_gap == pytest.approx(0.0)
    assert not reducible.is_irreducible
    assert reducible.period is None
    assert not reducible.stationary.is_unique


def test_tiny_positive_transitions_remain_structurally_and_numerically_visible() -> None:
    epsilon = 1e-13
    transition = np.array(
        [
            [1.0 - epsilon, epsilon],
            [2.0 * epsilon, 1.0 - 2.0 * epsilon],
        ]
    )
    result = analyze_markov_chain(transition)

    assert result.is_irreducible
    assert result.is_aperiodic
    assert result.stationary.is_unique
    np.testing.assert_allclose(
        result.stationary.probabilities,
        [2.0 / 3.0, 1.0 / 3.0],
        rtol=1e-12,
        atol=1e-14,
    )


def test_markov_simulation_is_reproducible_and_approaches_stationarity() -> None:
    transition = np.array([[0.9, 0.1], [0.2, 0.8]])
    first = simulate_markov_chain(
        transition,
        initial_state=0,
        n_steps=40,
        n_paths=30_000,
        rng=np.random.default_rng(61),
    )
    second = simulate_markov_chain(
        transition,
        initial_state=0,
        n_steps=40,
        n_paths=30_000,
        rng=np.random.default_rng(61),
    )
    np.testing.assert_array_equal(first, second)
    terminal_probability = np.mean(first[:, -1] == 0)
    assert terminal_probability == pytest.approx(2.0 / 3.0, abs=0.01)


def test_first_exit_times_respect_truncation() -> None:
    paths = np.array(
        [
            [0.0, 1.0, 2.0, 3.0],
            [0.0, -1.0, -2.0, -1.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
    )
    result = first_exit_times(paths, -2.0, 2.0)
    np.testing.assert_array_equal(result.stopping_times, [2, 2, 3])
    np.testing.assert_allclose(result.stopped_values, [2.0, -2.0, 0.0])
    np.testing.assert_array_equal(result.hit_boundary, [True, True, False])

    diagnostics = diagnose_optional_stopping(paths, -2.0, 2.0)
    assert diagnostics.boundary_hit_rate == pytest.approx(2.0 / 3.0)
    assert diagnostics.truncation_rate == pytest.approx(1.0 / 3.0)


def test_bounded_optional_stopping_agrees_with_martingale_expectation() -> None:
    result = random_walk_optional_stopping(
        n_paths=40_000,
        max_steps=100,
        lower_boundary=-5.0,
        upper_boundary=5.0,
        rng=np.random.default_rng(72),
    )
    assert result.boundary_hit_rate > 0.99
    assert abs(result.bias) < 3.0 * result.standard_error


@pytest.mark.parametrize(
    "transition",
    [
        [[0.8, 0.3], [0.2, 0.8]],
        [[1.1, -0.1], [0.0, 1.0]],
        [[1.0, np.nan], [0.0, 1.0]],
    ],
)
def test_transition_validation_rejects_invalid_values(transition) -> None:
    with pytest.raises(ValueError):
        validate_transition_matrix(transition)


def test_stationary_distribution_is_public_for_single_state_chain() -> None:
    result = stationary_distribution([[1.0]])
    np.testing.assert_allclose(result.probabilities, [1.0])
    assert result.spectral_gap == 1.0
