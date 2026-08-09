import numpy as np
import pytest
from quant_textbook import (
    conditional_gaussian,
    correlated_gaussian,
    covariance_factor,
    validate_covariance,
)


def test_conditional_gaussian_matches_closed_form() -> None:
    mean = np.array([1.0, -2.0, 0.5])
    covariance = np.array(
        [
            [4.0, 1.2, -0.4],
            [1.2, 3.0, 0.6],
            [-0.4, 0.6, 2.0],
        ]
    )
    observed_value = np.array([2.5])
    result = conditional_gaussian(mean, covariance, [1], observed_value)

    target = [0, 2]
    cross = covariance[np.ix_(target, [1])]
    expected_gain = cross / covariance[1, 1]
    expected_mean = mean[target] + expected_gain.ravel() * (observed_value[0] - mean[1])
    expected_covariance = covariance[np.ix_(target, target)] - expected_gain @ cross.T

    assert result.target_indices == (0, 2)
    np.testing.assert_allclose(result.gain, expected_gain)
    np.testing.assert_allclose(result.mean, expected_mean)
    np.testing.assert_allclose(result.covariance, expected_covariance, atol=1e-14)


def test_correlated_gaussian_reproduces_target_moments_and_seed() -> None:
    mean = np.array([0.5, -1.0])
    covariance = np.array([[1.5, 0.7], [0.7, 2.0]])
    first = correlated_gaussian(
        mean,
        covariance,
        100_000,
        rng=np.random.default_rng(19),
    )
    second = correlated_gaussian(
        mean,
        covariance,
        100_000,
        rng=np.random.default_rng(19),
    )

    assert first.shape == (100_000, 2)
    np.testing.assert_array_equal(first, second)
    np.testing.assert_allclose(first.mean(axis=0), mean, atol=0.015)
    np.testing.assert_allclose(np.cov(first, rowvar=False), covariance, atol=0.025)


def test_eigh_factor_supports_singular_and_near_singular_covariance() -> None:
    covariance = np.array([[1.0, 1.0], [1.0, 1.0]])
    diagnostics = validate_covariance(covariance)
    factor = covariance_factor(covariance)

    assert diagnostics.numerical_rank == 1
    assert np.isinf(diagnostics.condition_number)
    assert factor.method == "eigh"
    np.testing.assert_allclose(factor.factor @ factor.factor.T, covariance, atol=1e-14)
    with pytest.raises(np.linalg.LinAlgError, match="positive-definite"):
        covariance_factor(covariance, method="cholesky")


def test_covariance_rank_is_invariant_to_units_scaling() -> None:
    covariance = np.array([[2.0, 0.3], [0.3, 1.0]])
    base = validate_covariance(covariance)
    scaled = validate_covariance(1e-20 * covariance)

    assert base.numerical_rank == scaled.numerical_rank == 2
    assert base.condition_number == pytest.approx(scaled.condition_number)
    decomposition = covariance_factor(1e-20 * covariance)
    np.testing.assert_allclose(
        decomposition.factor @ decomposition.factor.T,
        1e-20 * covariance,
        rtol=1e-12,
        atol=1e-35,
    )

    tiny_singular = 1e-20 * np.array(
        [
            [1.0, 1.0, 0.5],
            [1.0, 1.0, 0.5],
            [0.5, 0.5, 1.0],
        ]
    )
    result = conditional_gaussian(
        np.zeros(3),
        tiny_singular,
        [0, 1],
        [7e-11, 7e-11],
    )
    assert result.observed_rank == 1

    with pytest.raises(ValueError, match="symmetric"):
        validate_covariance(1e-20 * np.array([[1.0, 0.9], [0.3, 1.0]]))


def test_singular_conditioning_checks_affine_support() -> None:
    mean = np.zeros(3)
    covariance = np.array(
        [
            [1.0, 1.0, 0.5],
            [1.0, 1.0, 0.5],
            [0.5, 0.5, 1.0],
        ]
    )
    consistent = conditional_gaussian(mean, covariance, [0, 1], [0.7, 0.7])
    assert consistent.observed_rank == 1
    assert consistent.mean[0] == pytest.approx(0.35)

    with pytest.raises(ValueError, match="singular Gaussian support"):
        conditional_gaussian(mean, covariance, [0, 1], [0.7, -0.7])


def test_full_rank_conditioning_accepts_all_finite_observed_values() -> None:
    observed_block = np.array([[1.0, 0.99999], [0.99999, 1.0]])
    covariance = np.block(
        [
            [observed_block, np.array([[0.1], [0.1]])],
            [np.array([[0.1, 0.1]]), np.array([[1.0]])],
        ]
    )
    result = conditional_gaussian(
        np.zeros(3),
        covariance,
        [0, 1],
        [1e8, -1e8],
    )
    assert result.observed_rank == 2
    assert np.all(np.isfinite(result.mean))


def test_conditioning_preserves_positive_support_below_numerical_rank_cutoff() -> None:
    covariance = np.diag([1.0, 1e-15, 1.0])
    samples = correlated_gaussian(
        np.zeros(3),
        covariance,
        8,
        rng=np.random.default_rng(29),
    )
    result = conditional_gaussian(
        np.zeros(3),
        covariance,
        [0, 1],
        [0.0, 1e-8],
    )

    assert np.any(samples[:, 1] != 0.0)
    assert result.observed_rank == 1
    assert np.all(np.isfinite(result.mean))
    np.testing.assert_allclose(result.covariance, [[1.0]])


def test_conditioning_falls_back_when_exact_rank_one_solve_fails() -> None:
    vector = np.array([1.3619485152698475e-5, 0.57176368104379927])
    observed_block = np.outer(vector, vector)
    assert np.linalg.eigvalsh(observed_block)[0] > 0.0
    with pytest.raises(np.linalg.LinAlgError):
        np.linalg.solve(observed_block, np.eye(2))
    covariance = np.block(
        [
            [observed_block, np.zeros((2, 1))],
            [np.zeros((1, 2)), np.ones((1, 1))],
        ]
    )

    result = conditional_gaussian(
        np.zeros(3),
        covariance,
        [0, 1],
        2.0 * vector,
    )

    assert result.observed_rank == 1
    np.testing.assert_allclose(result.mean, [0.0])
    np.testing.assert_allclose(result.covariance, [[1.0]])


@pytest.mark.parametrize(
    "covariance",
    [
        [[1.0, 2.0], [0.0, 1.0]],
        [[1.0, 2.0], [2.0, 1.0]],
        [[1.0, np.nan], [np.nan, 1.0]],
    ],
)
def test_covariance_validation_rejects_invalid_matrices(covariance) -> None:
    with pytest.raises(ValueError):
        validate_covariance(covariance)


def test_random_api_requires_generator() -> None:
    with pytest.raises(TypeError, match="Generator"):
        correlated_gaussian([0.0], [[1.0]], 4, rng=7)  # type: ignore[arg-type]
