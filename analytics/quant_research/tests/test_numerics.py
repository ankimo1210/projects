import numpy as np
import pytest
from quant_textbook import (
    add_intercept,
    align_component_signs,
    make_regression_dataset,
    pca_from_svd,
    solve_least_squares,
)


def test_least_squares_methods_agree_with_numpy_on_well_conditioned_data() -> None:
    dataset = make_regression_dataset(
        n_samples=120,
        n_features=4,
        noise_std=0.05,
        condition_number=5.0,
        seed=10,
    )
    expected, *_ = np.linalg.lstsq(dataset.X, dataset.y, rcond=None)

    for method in ("inverse", "normal", "qr", "svd"):
        result = solve_least_squares(dataset.X, dataset.y, method=method)
        np.testing.assert_allclose(result.coefficients, expected, rtol=1e-11, atol=1e-11)
        assert result.diagnostics.rank == dataset.X.shape[1]
        assert result.diagnostics.condition_number == pytest.approx(5.0)
        assert result.diagnostics.residual_norm == pytest.approx(
            np.linalg.norm(dataset.y - dataset.X @ expected)
        )


def test_weighted_and_ridge_solutions_match_direct_formulas() -> None:
    rng = np.random.default_rng(4)
    design = add_intercept(rng.normal(size=(80, 3)))
    response = design @ np.array([0.3, -1.0, 2.0, 0.5]) + rng.normal(0.0, 0.1, 80)
    weights = np.linspace(0.5, 2.0, 80)
    ridge = 0.7
    root_weights = np.sqrt(weights)
    weighted_design = root_weights[:, None] * design
    weighted_response = root_weights * response
    expected = np.linalg.solve(
        weighted_design.T @ weighted_design + ridge * np.eye(design.shape[1]),
        weighted_design.T @ weighted_response,
    )

    for method in ("inverse", "normal", "qr", "svd"):
        result = solve_least_squares(design, response, method=method, weights=weights, ridge=ridge)
        np.testing.assert_allclose(result.coefficients, expected, rtol=1e-11, atol=1e-11)
        assert result.diagnostics.weighted_residual_norm == pytest.approx(
            np.linalg.norm(root_weights * result.residuals)
        )


def test_explicit_inverse_is_an_unstable_ill_conditioned_baseline() -> None:
    x = np.linspace(0.99, 1.01, 60)
    design = np.vander(x, N=9, increasing=True)
    response = design @ np.arange(1.0, 10.0)
    stable = solve_least_squares(design, response, method="svd")
    assert stable.diagnostics.condition_number > 1e15

    try:
        unstable = solve_least_squares(design, response, method="inverse")
    except np.linalg.LinAlgError:
        return
    assert np.linalg.norm(unstable.residuals) > 100.0 * np.linalg.norm(stable.residuals)


def test_rank_deficient_design_is_supported_by_svd_but_not_qr() -> None:
    dataset = make_regression_dataset(
        n_samples=40, n_features=4, rank_deficient=True, noise_std=0.0, seed=3
    )
    svd = solve_least_squares(dataset.X, dataset.y, method="svd")
    assert svd.diagnostics.rank == 3
    np.testing.assert_allclose(svd.fitted_values, dataset.y, atol=1e-12)
    with pytest.raises(np.linalg.LinAlgError, match="rank-deficient"):
        solve_least_squares(dataset.X, dataset.y, method="qr")


def test_pca_reconstructs_full_data_and_reports_centered_variance() -> None:
    rng = np.random.default_rng(8)
    observations = rng.normal(size=(50, 5)) @ np.diag([4.0, 2.0, 1.0, 0.5, 0.1])
    result = pca_from_svd(observations)

    np.testing.assert_allclose(result.inverse_transform(), observations, atol=1e-12)
    np.testing.assert_allclose(result.transform(observations), result.scores, atol=1e-12)
    assert result.explained_variance_ratio.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(result.components @ result.components.T, np.eye(5), atol=1e-12)


def test_component_sign_alignment_preserves_reconstruction() -> None:
    rng = np.random.default_rng(13)
    observations = rng.normal(size=(40, 4))
    result = pca_from_svd(observations, n_components=3)
    signs = np.array([-1.0, 1.0, -1.0])
    candidates = result.components * signs[:, None]
    candidate_scores = result.scores * signs[None, :]

    aligned, aligned_scores = align_component_signs(
        candidates, result.components, scores=candidate_scores
    )
    np.testing.assert_allclose(aligned, result.components)
    np.testing.assert_allclose(aligned_scores, result.scores)
    np.testing.assert_allclose(candidate_scores @ candidates, result.scores @ result.components)


@pytest.mark.parametrize(
    ("design", "response", "kwargs", "message"),
    [
        (np.ones((3, 2)), np.ones(2), {}, "one entry per observation"),
        (np.ones((3, 2)), np.ones(3), {"ridge": -1.0}, "non-negative"),
        (np.ones((3, 2)), np.ones(3), {"weights": [1.0, 0.0, 1.0]}, "positive"),
        (np.ones((3, 2)), np.ones(3), {"method": "magic"}, "unknown"),
    ],
)
def test_least_squares_rejects_invalid_inputs(design, response, kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        solve_least_squares(design, response, **kwargs)


def test_pca_rejects_invalid_component_count() -> None:
    with pytest.raises(ValueError, match="between"):
        pca_from_svd(np.ones((3, 2)), n_components=3)
