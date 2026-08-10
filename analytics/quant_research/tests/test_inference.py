import numpy as np
import pytest
from quant_textbook import (
    evaluate_likelihood,
    finite_difference_gradient,
    finite_difference_hessian,
    fit_gaussian_mle,
    fit_logistic_mle,
    fit_poisson_mle,
    likelihood_ratio_test,
    score_test,
    summarize_coverage,
    wald_test,
)
from scipy.special import expit


@pytest.mark.parametrize(
    ("model", "parameters", "response"),
    [
        ("gaussian", np.array([0.2, -0.4, np.log(0.8)]), np.array([0.1, -0.2, 1.0, 0.5])),
        ("logistic", np.array([0.2, -0.4]), np.array([0.0, 1.0, 1.0, 0.0])),
        ("poisson", np.array([0.2, -0.4]), np.array([0.0, 1.0, 3.0, 2.0])),
    ],
)
def test_analytic_likelihood_derivatives_match_central_differences(
    model, parameters, response
) -> None:
    design = np.column_stack((np.ones(4), np.array([-1.0, 0.2, 0.7, 1.4])))

    def objective(theta):
        return evaluate_likelihood(model, theta, design, response).log_likelihood

    analytic = evaluate_likelihood(model, parameters, design, response)
    numeric_gradient = finite_difference_gradient(objective, parameters)
    numeric_hessian = finite_difference_hessian(objective, parameters)

    np.testing.assert_allclose(analytic.score, numeric_gradient, rtol=2e-6, atol=2e-6)
    np.testing.assert_allclose(analytic.hessian, numeric_hessian, rtol=2e-5, atol=2e-5)


def test_finite_difference_hessian_recovers_non_diagonal_quadratic() -> None:
    matrix = np.array([[3.0, -1.25, 0.4], [-1.25, 2.0, 0.75], [0.4, 0.75, 1.5]])

    def quadratic(point):
        return 0.5 * point @ matrix @ point + np.array([1.0, -2.0, 0.3]) @ point

    point = np.array([0.4, -1.1, 2.3])
    np.testing.assert_allclose(finite_difference_hessian(quadratic, point), matrix, atol=2e-7)


def test_gaussian_mle_matches_closed_form_and_documents_parameter_shapes() -> None:
    rng = np.random.default_rng(101)
    design = np.column_stack((np.ones(500), rng.normal(size=(500, 2))))
    response = design @ np.array([0.5, -1.2, 0.7]) + rng.normal(0.0, 0.8, 500)
    result = fit_gaussian_mle(design, response)
    expected, *_ = np.linalg.lstsq(design, response, rcond=None)
    residuals = response - design @ expected
    expected_scale = np.sqrt(np.mean(residuals**2))

    np.testing.assert_allclose(result.coefficients, expected, rtol=1e-12, atol=1e-12)
    assert result.scale == pytest.approx(expected_scale)
    assert result.parameters.shape == (design.shape[1] + 1,)
    assert result.parameters[-1] == pytest.approx(np.log(expected_scale))
    assert result.covariance.shape == (design.shape[1], design.shape[1])
    assert result.diagnostics.implemented_diagnostics_passed
    assert result.diagnostics.gradient_norm < 1e-10


def test_gaussian_covariance_is_stable_under_near_collinear_reparameterization() -> None:
    rng = np.random.default_rng(106)
    sample_size = 300
    first = rng.normal(size=sample_size)
    innovation = rng.normal(size=sample_size)
    epsilon = 1e-7
    stable_design = np.column_stack((np.ones(sample_size), first, innovation))
    raw_design = np.column_stack((np.ones(sample_size), first, first + epsilon * innovation))
    transformation = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, epsilon],
        ]
    )
    response = stable_design @ np.array([0.3, -0.5, 0.8]) + rng.normal(
        scale=0.7,
        size=sample_size,
    )

    raw_result = fit_gaussian_mle(raw_design, response)
    stable_result = fit_gaussian_mle(stable_design, response)
    inverse_transformation = np.linalg.inv(transformation)
    transformed_covariance = (
        inverse_transformation @ stable_result.covariance @ inverse_transformation.T
    )

    np.testing.assert_allclose(
        raw_result.covariance,
        transformed_covariance,
        rtol=5e-8,
        atol=2e-5,
    )


def test_gaussian_information_diagnostics_are_scale_invariant() -> None:
    rng = np.random.default_rng(107)
    raw_design = np.column_stack((np.ones(250), rng.normal(size=(250, 2))))
    response = raw_design @ np.array([0.4, -0.2, 0.7]) + rng.normal(size=250)
    reference = fit_gaussian_mle(raw_design, response)

    for factor in (1e-10, 1e10):
        result = fit_gaussian_mle(factor * raw_design, response)
        assert result.diagnostics.information_positive_definite
        assert result.diagnostics.implemented_diagnostics_passed
        assert result.diagnostics.hessian_condition_number == pytest.approx(
            reference.diagnostics.hessian_condition_number,
            rel=1e-10,
        )
        np.testing.assert_allclose(result.fitted_mean, reference.fitted_mean, atol=1e-11)
        np.testing.assert_allclose(
            result.coefficients * factor,
            reference.coefficients,
            atol=1e-10,
        )


def test_logistic_mle_recovers_coefficients_and_detects_complete_separation() -> None:
    rng = np.random.default_rng(102)
    predictor = rng.normal(size=2_000)
    design = np.column_stack((np.ones(predictor.size), predictor))
    truth = np.array([-0.3, 0.8])
    response = rng.binomial(1, expit(design @ truth))
    result = fit_logistic_mle(design, response, gradient_tolerance=1e-7)

    np.testing.assert_allclose(result.coefficients, truth, atol=0.12)
    assert result.diagnostics.optimizer_converged
    assert not result.diagnostics.separation_detected
    assert result.diagnostics.implemented_diagnostics_passed

    separated_response = (predictor > 0.0).astype(float)
    separated = fit_logistic_mle(
        design,
        separated_response,
        max_iterations=100,
        gradient_tolerance=1e-7,
    )
    assert separated.diagnostics.separation_detected
    assert not separated.diagnostics.implemented_diagnostics_passed
    assert any("separation" in warning for warning in separated.diagnostics.warnings)


def test_glm_fit_is_scale_invariant_from_the_default_start() -> None:
    rng = np.random.default_rng(103)
    raw_design = np.column_stack((np.ones(400), rng.normal(size=400)))
    response = rng.binomial(1, expit(raw_design @ np.array([0.1, -0.5])))
    reference = fit_logistic_mle(raw_design, response)

    for factor in (1e-10, 1e10):
        result = fit_logistic_mle(factor * raw_design, response)
        assert result.diagnostics.optimizer_converged
        assert result.diagnostics.information_positive_definite
        assert np.isfinite(result.diagnostics.hessian_condition_number)
        np.testing.assert_allclose(result.fitted_mean, reference.fitted_mean, atol=1e-10)
        assert result.log_likelihood == pytest.approx(reference.log_likelihood, abs=1e-10)
        np.testing.assert_allclose(
            result.coefficients * factor,
            reference.coefficients,
            atol=1e-9,
        )


@pytest.mark.parametrize("model", ["logistic", "poisson"])
def test_default_glm_convergence_uses_the_scaled_average_score(model) -> None:
    for seed in range(20):
        rng = np.random.default_rng(1_200 + seed)
        design = np.column_stack((np.ones(300), rng.normal(size=(300, 3))))
        truth = np.array([0.1, -0.3, 0.2, 0.4])
        linear_predictor = design @ truth
        response = (
            rng.binomial(1, expit(linear_predictor))
            if model == "logistic"
            else rng.poisson(np.exp(linear_predictor))
        )
        result = (
            fit_logistic_mle(design, response)
            if model == "logistic"
            else fit_poisson_mle(design, response)
        )

        assert result.diagnostics.optimizer_converged
        assert result.diagnostics.average_gradient_norm <= np.sqrt(np.finfo(float).eps)


def test_logistic_mle_detects_quasi_complete_separation() -> None:
    predictor = np.concatenate((np.zeros(40), np.ones(40)))
    response = np.concatenate(
        (
            np.tile(np.array([0.0, 1.0]), 20),
            np.ones(40),
        )
    )
    design = np.column_stack((np.ones(predictor.size), predictor))

    result = fit_logistic_mle(design, response)

    assert result.diagnostics.separation_detected
    assert not result.diagnostics.implemented_diagnostics_passed
    assert any("quasi-complete" in warning for warning in result.diagnostics.warnings)


def test_poisson_mle_recovers_mean_and_flags_overdispersion() -> None:
    rng = np.random.default_rng(104)
    predictor = rng.normal(size=2_000)
    design = np.column_stack((np.ones(predictor.size), predictor))
    truth = np.array([0.3, -0.25])
    mean = np.exp(design @ truth)
    response = rng.poisson(mean)
    result = fit_poisson_mle(design, response, gradient_tolerance=1e-7)

    np.testing.assert_allclose(result.coefficients, truth, atol=0.08)
    assert result.diagnostics.optimizer_converged
    assert result.diagnostics.overdispersion_ratio == pytest.approx(1.0, abs=0.12)
    assert not result.diagnostics.overdispersion_detected

    latent_mean = mean * rng.gamma(shape=0.5, scale=2.0, size=mean.size)
    overdispersed = fit_poisson_mle(
        design,
        rng.poisson(latent_mean),
        gradient_tolerance=1e-7,
    )
    assert overdispersed.diagnostics.overdispersion_ratio > 1.5
    assert overdispersed.diagnostics.overdispersion_detected
    assert not overdispersed.diagnostics.implemented_diagnostics_passed


def test_poisson_mle_detects_zero_count_separation() -> None:
    positive_counts = np.tile(np.array([1.0, 2.0, 3.0, 2.0]), 10)
    response = np.concatenate((positive_counts, np.zeros(40)))
    group = np.concatenate((np.zeros(40), np.ones(40)))
    design = np.column_stack((np.ones(response.size), group))

    result = fit_poisson_mle(design, response)

    assert result.diagnostics.separation_detected
    assert not result.diagnostics.implemented_diagnostics_passed
    assert any("zero-count separation" in warning for warning in result.diagnostics.warnings)


def test_all_zero_poisson_counts_depend_on_the_design_recession_directions() -> None:
    separated = fit_poisson_mle(np.ones((20, 1)), np.zeros(20))
    assert separated.diagnostics.separation_detected
    assert not separated.diagnostics.implemented_diagnostics_passed

    symmetric_design = np.array([[-1.0], [1.0]])
    finite = fit_poisson_mle(symmetric_design, np.zeros(2))
    assert not finite.diagnostics.separation_detected
    assert finite.diagnostics.optimizer_converged
    assert finite.coefficients[0] == pytest.approx(0.0, abs=1e-10)


def test_lr_wald_and_score_statistics_match_closed_forms() -> None:
    lr = likelihood_ratio_test(-100.0, -102.0, 2)
    assert lr.statistic == pytest.approx(4.0)
    assert lr.degrees_of_freedom == 2
    assert 0.0 < lr.p_value < 1.0

    estimate = np.array([1.0, -0.5])
    covariance = np.diag([0.25, 1.0])
    wald = wald_test(estimate, covariance, np.eye(2))
    assert wald.statistic == pytest.approx(4.25)
    assert wald.degrees_of_freedom == 2

    score = score_test(np.array([2.0, 1.0]), np.diag([4.0, 2.0]))
    assert score.statistic == pytest.approx(1.5)
    assert score.degrees_of_freedom == 2


def test_coverage_summary_separates_empirical_sd_from_model_se() -> None:
    rng = np.random.default_rng(105)
    estimates = rng.normal(2.0, 0.2, 10_000)
    standard_errors = np.full(estimates.size, 0.2)
    summary = summarize_coverage(estimates, standard_errors, 2.0)

    assert summary.empirical_bias == pytest.approx(0.0, abs=0.006)
    assert summary.empirical_standard_deviation == pytest.approx(0.2, rel=0.02)
    assert summary.standard_error_ratio == pytest.approx(1.0, rel=0.02)
    assert summary.coverage == pytest.approx(0.95, abs=0.01)
    assert summary.coverage_monte_carlo_error > 0.0


@pytest.mark.parametrize(
    ("function", "message"),
    [
        (
            lambda: evaluate_likelihood("logistic", [0.0], np.ones((2, 1)), [0.0, 2.0]),
            "zero and one",
        ),
        (
            lambda: evaluate_likelihood("poisson", [0.0], np.ones((2, 1)), [0.0, 1.5]),
            "integer counts",
        ),
        (
            lambda: likelihood_ratio_test(-3.0, -2.0, 1),
            "must not be below",
        ),
        (
            lambda: summarize_coverage([1.0, 2.0], [0.1, -0.1], 1.0),
            "non-negative",
        ),
    ],
)
def test_inference_rejects_invalid_inputs(function, message) -> None:
    with pytest.raises(ValueError, match=message):
        function()
