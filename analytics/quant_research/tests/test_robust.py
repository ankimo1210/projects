import numpy as np
import pandas as pd
import pytest
from quant_textbook import fit_ols_inference, ols_covariance


def test_naive_covariance_matches_homoskedastic_closed_form() -> None:
    rng = np.random.default_rng(301)
    design = np.column_stack((np.ones(200), rng.normal(size=(200, 2))))
    response = design @ np.array([0.2, -0.5, 1.0]) + rng.normal(0.0, 0.7, 200)
    result = fit_ols_inference(design, response, covariance_type="naive")
    bread = np.linalg.inv(design.T @ design)
    expected = (result.residuals @ result.residuals / (200 - 3)) * bread

    np.testing.assert_allclose(result.covariance, expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result.standard_errors**2, np.diag(expected))
    assert result.diagnostics.covariance.dependence_assumption.startswith("homoskedastic")


@pytest.mark.parametrize("covariance_type", ["HC0", "HC1", "HC2", "HC3"])
def test_hc_covariances_match_sandwich_formulas(covariance_type) -> None:
    rng = np.random.default_rng(302)
    design = np.column_stack((np.ones(80), rng.normal(size=(80, 2))))
    response = design @ np.array([1.0, 0.3, -0.4]) + rng.normal(size=80)
    coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
    residuals = response - design @ coefficients
    bread = np.linalg.inv(design.T @ design)
    leverage = np.einsum("ij,jk,ik->i", design, bread, design)
    squared = residuals**2
    if covariance_type == "HC1":
        squared *= design.shape[0] / (design.shape[0] - design.shape[1])
    elif covariance_type == "HC2":
        squared /= 1.0 - leverage
    elif covariance_type == "HC3":
        squared /= (1.0 - leverage) ** 2
    expected = bread @ (design.T @ (squared[:, None] * design)) @ bread
    actual = ols_covariance(design, residuals, covariance_type=covariance_type)

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_hac_covariance_matches_bartlett_weighted_score_products() -> None:
    design = np.column_stack((np.ones(8), np.linspace(-1.0, 1.0, 8)))
    residuals = np.array([0.2, -0.1, 0.5, 0.3, -0.4, -0.2, 0.1, -0.3])
    bread = np.linalg.inv(design.T @ design)
    scores = design * residuals[:, None]
    meat = scores.T @ scores
    for lag in (1, 2):
        weight = 1.0 - lag / 3.0
        cross = scores[lag:].T @ scores[:-lag]
        meat += weight * (cross + cross.T)
    expected = bread @ meat @ bread
    actual = ols_covariance(
        design,
        residuals,
        covariance_type="HAC",
        max_lag=2,
        small_sample=False,
    )

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_cluster_covariance_matches_cluster_aggregated_scores() -> None:
    design = np.column_stack((np.ones(12), np.linspace(-1.0, 1.0, 12)))
    residuals = np.array([0.2, -0.1, 0.4, -0.2, 0.1, -0.3, 0.5, -0.2, 0.2, -0.1, 0.3, -0.4])
    clusters = np.repeat(["a", "b", "c", "d"], 3)
    bread = np.linalg.inv(design.T @ design)
    scores = design * residuals[:, None]
    cluster_scores = np.vstack(
        [scores[clusters == label].sum(axis=0) for label in np.unique(clusters)]
    )
    expected = bread @ (cluster_scores.T @ cluster_scores) @ bread
    actual = ols_covariance(
        design,
        residuals,
        covariance_type="cluster",
        clusters=clusters,
        small_sample=False,
    )

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_hc3_mean_se_tracks_monte_carlo_sd_under_heteroskedasticity() -> None:
    rng = np.random.default_rng(303)
    predictor = np.linspace(-2.0, 2.0, 160)
    design = np.column_stack((np.ones(predictor.size), predictor))
    slope_estimates = []
    naive_standard_errors = []
    robust_standard_errors = []
    for _ in range(500):
        error_scale = 0.2 + 1.2 * np.abs(predictor)
        response = 0.5 + 0.8 * predictor + rng.normal(0.0, error_scale)
        naive = fit_ols_inference(design, response, covariance_type="naive")
        robust = fit_ols_inference(design, response, covariance_type="HC3")
        slope_estimates.append(robust.coefficients[1])
        naive_standard_errors.append(naive.standard_errors[1])
        robust_standard_errors.append(robust.standard_errors[1])
    empirical_sd = np.std(slope_estimates, ddof=1)
    naive_error = abs(np.mean(naive_standard_errors) - empirical_sd)
    robust_error = abs(np.mean(robust_standard_errors) - empirical_sd)

    assert robust_error < 0.35 * naive_error


def test_hac_and_cluster_diagnostics_record_dependence_choices() -> None:
    rng = np.random.default_rng(304)
    design = np.column_stack((np.ones(120), rng.normal(size=120)))
    response = design @ np.array([0.2, 0.4]) + rng.normal(size=120)
    hac = fit_ols_inference(design, response, covariance_type="HAC", max_lag=4)
    cluster = fit_ols_inference(
        design,
        response,
        covariance_type="cluster",
        clusters=np.repeat(np.arange(20), 6),
    )

    assert hac.diagnostics.covariance.max_lag == 4
    assert hac.diagnostics.covariance.small_sample_correction
    assert cluster.diagnostics.covariance.n_clusters == 20
    assert any("fewer than 30" in warning for warning in cluster.diagnostics.covariance.warnings)
    assert "omitted-variable" in cluster.diagnostics.remaining_bias_warning


@pytest.mark.parametrize(
    ("covariance_type", "extra_arguments"),
    [
        ("HC3", {}),
        ("HAC", {"max_lag": 3, "small_sample": False}),
        (
            "cluster",
            {"clusters": np.repeat(np.arange(40), 5), "small_sample": False},
        ),
    ],
)
def test_qr_covariance_is_stable_under_near_collinear_reparameterization(
    covariance_type, extra_arguments
) -> None:
    rng = np.random.default_rng(305)
    n_observations = 200
    stable_predictor = rng.normal(size=n_observations)
    perturbation = rng.normal(size=n_observations)
    epsilon = 1e-7
    stable_design = np.column_stack((np.ones(n_observations), stable_predictor, perturbation))
    near_collinear_design = np.column_stack(
        (
            np.ones(n_observations),
            stable_predictor,
            stable_predictor + epsilon * perturbation,
        )
    )
    transformation = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, epsilon],
        ]
    )
    residuals = rng.normal(size=n_observations)

    near_collinear_covariance = ols_covariance(
        near_collinear_design,
        residuals,
        covariance_type=covariance_type,
        **extra_arguments,
    )
    stable_covariance = ols_covariance(
        stable_design,
        residuals,
        covariance_type=covariance_type,
        **extra_arguments,
    )

    assert np.linalg.cond(near_collinear_design) > 1e7
    np.testing.assert_allclose(
        transformation @ near_collinear_covariance @ transformation.T,
        stable_covariance,
        # Materializing covariance in the ill-conditioned coefficient basis
        # loses some digits before transforming back.  The QR calculation
        # keeps this below 5%; the former normal-equation path exceeded 1000%.
        rtol=0.05,
        atol=1e-9,
    )


@pytest.mark.parametrize("factor", [1e-14, 1e14])
def test_ols_inference_is_invariant_to_predictor_units(factor) -> None:
    rng = np.random.default_rng(306)
    predictor = rng.normal(size=250)
    design = np.column_stack((np.ones(predictor.size), predictor))
    response = 0.4 - 0.7 * predictor + rng.normal(size=predictor.size)
    reference = fit_ols_inference(design, response, covariance_type="HC3")
    scaled_design = design.copy()
    scaled_design[:, 1] *= factor
    scaled = fit_ols_inference(scaled_design, response, covariance_type="HC3")
    parameter_map = np.diag([1.0, factor])

    np.testing.assert_allclose(scaled.fitted_values, reference.fitted_values, atol=1e-11)
    np.testing.assert_allclose(
        parameter_map @ scaled.coefficients,
        reference.coefficients,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        parameter_map @ scaled.covariance @ parameter_map.T,
        reference.covariance,
        rtol=1e-10,
        atol=1e-12,
    )
    assert scaled.diagnostics.scaled_design_condition_number == pytest.approx(
        reference.diagnostics.scaled_design_condition_number,
        rel=1e-12,
    )


@pytest.mark.parametrize("missing_label", [pd.NA, pd.NaT])
def test_cluster_covariance_rejects_pandas_missing_labels(missing_label) -> None:
    design = np.column_stack((np.ones(8), np.arange(8.0)))
    labels = np.array(["a", "a", "b", "b", "c", "c", "d", missing_label], dtype=object)

    with pytest.raises(ValueError, match="missing"):
        fit_ols_inference(
            design,
            np.arange(8.0),
            covariance_type="cluster",
            clusters=labels,
        )


@pytest.mark.parametrize(
    ("function", "error_type", "message"),
    [
        (
            lambda: fit_ols_inference(np.ones((5, 2)), np.arange(5.0)),
            np.linalg.LinAlgError,
            "full-column-rank",
        ),
        (
            lambda: ols_covariance(
                np.column_stack((np.ones(5), np.arange(5.0))),
                np.ones(5),
                covariance_type="cluster",
            ),
            ValueError,
            "clusters are required",
        ),
        (
            lambda: ols_covariance(
                np.column_stack((np.ones(5), np.arange(5.0))),
                np.ones(5),
                covariance_type="HAC",
                max_lag=5,
            ),
            ValueError,
            "between zero",
        ),
    ],
)
def test_robust_covariance_rejects_invalid_contracts(function, error_type, message) -> None:
    with pytest.raises(error_type, match=message):
        function()
