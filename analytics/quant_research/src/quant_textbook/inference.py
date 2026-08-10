"""Likelihood and finite-sample inference primitives for B3.

The routines in this module keep three questions separate: what parameter is
being estimated, whether the numerical optimizer stopped, and whether the
statistical model passed its diagnostics.  Gaussian, logistic, and Poisson
models use their analytic scores and Hessians; finite differences are exposed
only as an independent teaching and validation tool.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import linprog, minimize
from scipy.special import expit, gammaln
from scipy.stats import chi2

FloatArray = NDArray[np.float64]
LikelihoodModel = Literal["gaussian", "logistic", "poisson"]


def _design_response(X: ArrayLike, y: ArrayLike) -> tuple[FloatArray, FloatArray]:
    design = np.asarray(X, dtype=float)
    response = np.asarray(y, dtype=float)
    if design.ndim != 2 or design.shape[0] < 1 or design.shape[1] < 1:
        raise ValueError("X must be a non-empty two-dimensional array")
    if response.ndim != 1 or response.shape[0] != design.shape[0]:
        raise ValueError("y must be one-dimensional with one entry per row of X")
    if not np.all(np.isfinite(design)) or not np.all(np.isfinite(response)):
        raise ValueError("X and y must contain only finite values")
    return design, response


def _vector(values: ArrayLike, *, name: str, size: int | None = None) -> FloatArray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if size is not None and result.size != size:
        raise ValueError(f"{name} must contain exactly {size} entries")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _positive_integer(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be strictly positive")
    return int(value)


def _confidence_level(value: float) -> float:
    level = float(value)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    return level


@dataclass(frozen=True)
class LikelihoodEvaluation:
    """Log-likelihood, analytic score, and analytic Hessian at one point."""

    model: LikelihoodModel
    parameters: FloatArray
    log_likelihood: float
    score: FloatArray
    hessian: FloatArray


def evaluate_likelihood(
    model: LikelihoodModel,
    parameters: ArrayLike,
    X: ArrayLike,
    y: ArrayLike,
) -> LikelihoodEvaluation:
    """Evaluate a canonical B3 likelihood and its first two derivatives.

    Gaussian parameters are ``[beta_1, ..., beta_p, log_sigma]``.  Logistic
    and Poisson parameters contain only the regression coefficients.  The
    logarithmic scale makes the Gaussian standard deviation strictly positive.
    """

    if model not in {"gaussian", "logistic", "poisson"}:
        raise ValueError(f"unknown likelihood model: {model!r}")
    design, response = _design_response(X, y)
    parameter_count = design.shape[1] + (model == "gaussian")
    theta = _vector(parameters, name="parameters", size=parameter_count)

    if model == "gaussian":
        coefficients = theta[:-1]
        log_scale = float(theta[-1])
        inverse_variance = float(np.exp(-2.0 * log_scale))
        if not np.isfinite(inverse_variance) or inverse_variance <= 0.0:
            raise FloatingPointError("Gaussian scale produced non-finite arithmetic")
        residuals = response - design @ coefficients
        residual_sum_squares = float(residuals @ residuals)
        log_likelihood = (
            -0.5 * response.size * np.log(2.0 * np.pi)
            - response.size * log_scale
            - 0.5 * inverse_variance * residual_sum_squares
        )
        score_beta = inverse_variance * (design.T @ residuals)
        score_scale = -response.size + inverse_variance * residual_sum_squares
        hessian_beta = -inverse_variance * (design.T @ design)
        hessian_cross = -2.0 * inverse_variance * (design.T @ residuals)
        hessian = np.empty((theta.size, theta.size), dtype=float)
        hessian[:-1, :-1] = hessian_beta
        hessian[:-1, -1] = hessian_cross
        hessian[-1, :-1] = hessian_cross
        hessian[-1, -1] = -2.0 * inverse_variance * residual_sum_squares
        score = np.append(score_beta, score_scale)
    elif model == "logistic":
        if not np.all((response == 0.0) | (response == 1.0)):
            raise ValueError("logistic y must contain only zero and one")
        linear_predictor = design @ theta
        fitted = expit(linear_predictor)
        log_likelihood = float(
            np.sum(response * linear_predictor - np.logaddexp(0.0, linear_predictor))
        )
        score = design.T @ (response - fitted)
        weights = fitted * (1.0 - fitted)
        hessian = -(design.T @ (weights[:, None] * design))
    else:
        if np.any(response < 0.0) or not np.all(response == np.floor(response)):
            raise ValueError("Poisson y must contain non-negative integer counts")
        linear_predictor = design @ theta
        with np.errstate(over="ignore"):
            fitted = np.exp(linear_predictor)
        if not np.all(np.isfinite(fitted)):
            raise FloatingPointError("Poisson mean overflowed; rescale X or use a safer start")
        log_likelihood = float(
            np.sum(response * linear_predictor - fitted - gammaln(response + 1.0))
        )
        score = design.T @ (response - fitted)
        hessian = -(design.T @ (fitted[:, None] * design))

    if (
        not np.isfinite(log_likelihood)
        or not np.all(np.isfinite(score))
        or not np.all(np.isfinite(hessian))
    ):
        raise FloatingPointError("likelihood evaluation produced non-finite values")
    return LikelihoodEvaluation(
        model=model,
        parameters=theta.copy(),
        log_likelihood=float(log_likelihood),
        score=np.asarray(score, dtype=float),
        hessian=np.asarray(hessian, dtype=float),
    )


def finite_difference_gradient(
    function: Callable[[FloatArray], float],
    point: ArrayLike,
    *,
    relative_step: float = 1e-6,
) -> FloatArray:
    """Return a central finite-difference gradient with coordinate scaling."""

    if not callable(function):
        raise TypeError("function must be callable")
    location = _vector(point, name="point")
    step_scale = float(relative_step)
    if not np.isfinite(step_scale) or step_scale <= 0.0:
        raise ValueError("relative_step must be finite and strictly positive")
    gradient = np.empty(location.size, dtype=float)
    for index in range(location.size):
        step = step_scale * max(1.0, abs(float(location[index])))
        upper = location.copy()
        lower = location.copy()
        upper[index] += step
        lower[index] -= step
        upper_value = float(function(upper))
        lower_value = float(function(lower))
        if not np.isfinite(upper_value) or not np.isfinite(lower_value):
            raise FloatingPointError("function returned a non-finite value")
        gradient[index] = (upper_value - lower_value) / (2.0 * step)
    return gradient


def finite_difference_hessian(
    function: Callable[[FloatArray], float],
    point: ArrayLike,
    *,
    relative_step: float = 1e-4,
) -> FloatArray:
    """Return a symmetric central finite-difference Hessian."""

    if not callable(function):
        raise TypeError("function must be callable")
    location = _vector(point, name="point")
    step_scale = float(relative_step)
    if not np.isfinite(step_scale) or step_scale <= 0.0:
        raise ValueError("relative_step must be finite and strictly positive")
    steps = step_scale * np.maximum(1.0, np.abs(location))
    center = float(function(location.copy()))
    if not np.isfinite(center):
        raise FloatingPointError("function returned a non-finite value")
    hessian = np.empty((location.size, location.size), dtype=float)
    for first in range(location.size):
        upper = location.copy()
        lower = location.copy()
        upper[first] += steps[first]
        lower[first] -= steps[first]
        upper_value = float(function(upper))
        lower_value = float(function(lower))
        hessian[first, first] = (upper_value - 2.0 * center + lower_value) / steps[first] ** 2
        for second in range(first):
            plus_plus = location.copy()
            plus_minus = location.copy()
            minus_plus = location.copy()
            minus_minus = location.copy()
            plus_plus[[first, second]] += steps[[first, second]]
            plus_minus[first] += steps[first]
            plus_minus[second] -= steps[second]
            minus_plus[first] -= steps[first]
            minus_plus[second] += steps[second]
            minus_minus[[first, second]] -= steps[[first, second]]
            values = np.array(
                [
                    function(plus_plus),
                    function(plus_minus),
                    function(minus_plus),
                    function(minus_minus),
                ],
                dtype=float,
            )
            if not np.all(np.isfinite(values)):
                raise FloatingPointError("function returned a non-finite value")
            mixed = (values[0] - values[1] - values[2] + values[3]) / (
                4.0 * steps[first] * steps[second]
            )
            hessian[first, second] = mixed
            hessian[second, first] = mixed
    if not np.all(np.isfinite(hessian)):
        raise FloatingPointError("finite-difference Hessian is non-finite")
    return hessian


@dataclass(frozen=True)
class MLEDiagnostics:
    """Numerical and implemented model checks kept separate from estimates.

    ``implemented_diagnostics_passed`` means that the checks implemented by
    this module passed; it is not proof that the sampling or identification
    assumptions are correct.
    """

    optimizer_converged: bool
    optimizer_status: int
    optimizer_message: str
    iterations: int
    gradient_norm: float
    average_gradient_norm: float
    hessian_condition_number: float
    information_positive_definite: bool
    design_rank: int
    residual_degrees_of_freedom: int
    separation_detected: bool
    overdispersion_ratio: float
    overdispersion_detected: bool
    implemented_diagnostics_passed: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MLEResult:
    """MLE point estimate, model-based covariance, and diagnostics.

    ``covariance`` always corresponds to ``coefficients``.  For a Gaussian
    model, ``parameters`` additionally ends with ``log_sigma`` while the
    coefficient covariance remains the familiar ``p`` by ``p`` beta block.
    """

    model: LikelihoodModel
    parameters: FloatArray
    coefficients: FloatArray
    scale: float
    covariance: FloatArray
    standard_errors: FloatArray
    fitted_mean: FloatArray
    residuals: FloatArray
    log_likelihood: float
    n_observations: int
    diagnostics: MLEDiagnostics


def _information_diagnostics(information: FloatArray) -> tuple[bool, float]:
    symmetric = 0.5 * (information + information.T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    largest = float(np.max(np.abs(eigenvalues)))
    tolerance = np.finfo(float).eps * max(1, information.shape[0]) * largest
    positive_definite = bool(np.all(eigenvalues > tolerance))
    condition_number = float(np.linalg.cond(symmetric))
    return positive_definite, condition_number


def _inverse_information(information: FloatArray) -> FloatArray:
    positive_definite, _ = _information_diagnostics(information)
    if positive_definite:
        return np.linalg.inv(information)
    return np.linalg.pinv(information, hermitian=True)


def _scaled_design(design: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Return a column-scaled design and the raw-to-scaled parameter map."""

    column_scales = np.max(np.abs(design), axis=0)
    if np.any(column_scales == 0.0):
        raise np.linalg.LinAlgError("the design contains an all-zero column")
    scaled = design / column_scales
    if not np.all(np.isfinite(scaled)):
        raise FloatingPointError("design scaling produced non-finite values")
    return scaled, column_scales


def _logistic_separation(design: FloatArray, response: FloatArray) -> bool:
    """Detect complete or quasi-complete separation by a bounded LP.

    With signed rows ``a_i``, separation exists when a non-zero direction has
    ``a_i @ beta >= 0`` for every observation and at least one strict margin.
    The L1 bound removes the homogeneous scaling ambiguity.  ``design`` is
    already column-scaled by the caller, so the objective tolerance is not a
    hidden function of the input units.
    """

    if np.unique(response).size < 2:
        return True
    signed_design = np.where(response[:, None] == 1.0, design, -design)
    parameter_count = design.shape[1]
    margin_sum = signed_design.sum(axis=0)
    objective = -np.concatenate((margin_sum, -margin_sum))
    margin_constraints = np.column_stack((-signed_design, signed_design))
    l1_constraint = np.ones((1, 2 * parameter_count), dtype=float)
    feasibility = linprog(
        objective,
        A_ub=np.vstack((margin_constraints, l1_constraint)),
        b_ub=np.append(np.zeros(response.size), 1.0),
        bounds=[(0.0, None)] * (2 * parameter_count),
        method="highs",
    )
    if not feasibility.success:
        raise RuntimeError(f"logistic separation diagnostic failed: {feasibility.message}")
    maximum_margin_sum = -float(feasibility.fun)
    tolerance = 1_000.0 * np.finfo(float).eps * max(1, response.size, parameter_count)
    return bool(maximum_margin_sum > tolerance)


def _poisson_separation(design: FloatArray, response: FloatArray) -> bool:
    """Detect a Poisson recession direction that prevents a finite MLE.

    Along a separating direction, positive-count rows must have zero change in
    their linear predictors, while zero-count rows may only decrease and at
    least one must decrease strictly.  An L1 bound removes scale ambiguity.
    """

    zero_rows = response == 0.0
    if not np.any(zero_rows):
        return False
    positive_design = design[~zero_rows]
    zero_design = design[zero_rows]
    parameter_count = design.shape[1]
    objective_direction = zero_design.sum(axis=0)
    objective = np.concatenate((objective_direction, -objective_direction))
    inequality_matrix = np.vstack(
        (
            np.column_stack((zero_design, -zero_design)),
            np.ones((1, 2 * parameter_count), dtype=float),
        )
    )
    equality_matrix = (
        np.column_stack((positive_design, -positive_design)) if positive_design.size else None
    )
    feasibility = linprog(
        objective,
        A_ub=inequality_matrix,
        b_ub=np.append(np.zeros(zero_design.shape[0]), 1.0),
        A_eq=equality_matrix,
        b_eq=(np.zeros(positive_design.shape[0]) if positive_design.size else None),
        bounds=[(0.0, None)] * (2 * parameter_count),
        method="highs",
    )
    if not feasibility.success:
        raise RuntimeError(f"Poisson separation diagnostic failed: {feasibility.message}")
    minimum_zero_margin_sum = float(feasibility.fun)
    tolerance = 1_000.0 * np.finfo(float).eps * max(1, response.size, parameter_count)
    return bool(minimum_zero_margin_sum < -tolerance)


def fit_gaussian_mle(X: ArrayLike, y: ArrayLike) -> MLEResult:
    """Fit homoskedastic Gaussian linear regression by its closed-form MLE."""

    design, response = _design_response(X, y)
    n_observations, n_parameters = design.shape
    optimization_design, column_scales = _scaled_design(design)
    rank = int(np.linalg.matrix_rank(optimization_design))
    if n_observations <= n_parameters:
        raise ValueError("Gaussian MLE requires more observations than coefficients")
    if rank < n_parameters:
        raise np.linalg.LinAlgError("Gaussian MLE requires a full-column-rank design")
    scaled_coefficients, *_ = np.linalg.lstsq(
        optimization_design,
        response,
        rcond=None,
    )
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        coefficients = scaled_coefficients / column_scales
    if not np.all(np.isfinite(coefficients)):
        raise FloatingPointError("fitted parameters cannot be represented in the input units")
    fitted = optimization_design @ scaled_coefficients
    residuals = response - fitted
    variance = float(residuals @ residuals / n_observations)
    if variance <= np.finfo(float).tiny:
        raise ValueError("Gaussian scale MLE is zero; the likelihood has no interior optimum")
    scale = float(np.sqrt(variance))
    parameters = np.append(coefficients, np.log(scale))
    evaluation = evaluate_likelihood(
        "gaussian",
        np.append(scaled_coefficients, np.log(scale)),
        optimization_design,
        response,
    )
    information = -evaluation.hessian
    positive_definite, condition_number = _information_diagnostics(information)
    _, triangular_factor = np.linalg.qr(optimization_design, mode="reduced")
    triangular_inverse = np.linalg.solve(
        triangular_factor,
        np.eye(n_parameters, dtype=float),
    )
    scaled_covariance = variance * (triangular_inverse @ triangular_inverse.T)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        inverse_scales = 1.0 / column_scales
        coefficient_covariance = scaled_covariance * np.outer(
            inverse_scales,
            inverse_scales,
        )
    if not np.all(np.isfinite(coefficient_covariance)):
        raise FloatingPointError("coefficient covariance cannot be represented in the input units")
    warnings: list[str] = []
    if not positive_definite:
        warnings.append("observed information is not numerically positive definite")
    diagnostics = MLEDiagnostics(
        optimizer_converged=True,
        optimizer_status=0,
        optimizer_message="closed-form solution",
        iterations=0,
        gradient_norm=float(np.linalg.norm(evaluation.score, ord=np.inf)),
        average_gradient_norm=float(np.linalg.norm(evaluation.score, ord=np.inf) / n_observations),
        hessian_condition_number=condition_number,
        information_positive_definite=positive_definite,
        design_rank=rank,
        residual_degrees_of_freedom=n_observations - n_parameters,
        separation_detected=False,
        overdispersion_ratio=float("nan"),
        overdispersion_detected=False,
        implemented_diagnostics_passed=positive_definite,
        warnings=tuple(warnings),
    )
    return MLEResult(
        model="gaussian",
        parameters=parameters,
        coefficients=np.asarray(coefficients, dtype=float),
        scale=scale,
        covariance=coefficient_covariance,
        standard_errors=np.sqrt(np.diag(coefficient_covariance)),
        fitted_mean=fitted,
        residuals=residuals,
        log_likelihood=evaluation.log_likelihood,
        n_observations=n_observations,
        diagnostics=diagnostics,
    )


def _fit_glm_mle(
    model: Literal["logistic", "poisson"],
    X: ArrayLike,
    y: ArrayLike,
    *,
    initial: ArrayLike | None,
    max_iterations: int,
    gradient_tolerance: float,
) -> MLEResult:
    design, response = _design_response(X, y)
    n_observations, n_parameters = design.shape
    if n_observations <= n_parameters:
        raise ValueError(f"{model} MLE requires more observations than coefficients")
    optimization_design, column_scales = _scaled_design(design)
    rank = int(np.linalg.matrix_rank(optimization_design))
    if rank < n_parameters:
        raise np.linalg.LinAlgError(f"{model} MLE requires a full-column-rank design")
    if model == "logistic":
        if not np.all((response == 0.0) | (response == 1.0)):
            raise ValueError("logistic y must contain only zero and one")
        separation = _logistic_separation(optimization_design, response)
    else:
        if np.any(response < 0.0) or not np.all(response == np.floor(response)):
            raise ValueError("Poisson y must contain non-negative integer counts")
        separation = _poisson_separation(optimization_design, response)
    iteration_limit = _positive_integer(max_iterations, name="max_iterations")
    tolerance = float(gradient_tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("gradient_tolerance must be finite and strictly positive")
    raw_start = (
        np.zeros(n_parameters, dtype=float)
        if initial is None
        else _vector(initial, name="initial", size=n_parameters).copy()
    )
    with np.errstate(over="ignore", invalid="ignore"):
        start = raw_start * column_scales
    if not np.all(np.isfinite(start)):
        raise FloatingPointError("initial parameters overflowed in the scaled coordinates")

    def objective(parameters: FloatArray) -> float:
        return -evaluate_likelihood(
            model,
            parameters,
            optimization_design,
            response,
        ).log_likelihood

    def gradient(parameters: FloatArray) -> FloatArray:
        return -evaluate_likelihood(
            model,
            parameters,
            optimization_design,
            response,
        ).score

    def hessian(parameters: FloatArray) -> FloatArray:
        return -evaluate_likelihood(
            model,
            parameters,
            optimization_design,
            response,
        ).hessian

    optimization = minimize(
        objective,
        start,
        jac=gradient,
        hess=hessian,
        method="Newton-CG",
        options={"xtol": np.sqrt(np.finfo(float).eps), "maxiter": iteration_limit},
    )
    scaled_parameters = np.asarray(optimization.x, dtype=float)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        parameters = scaled_parameters / column_scales
    if not np.all(np.isfinite(parameters)):
        raise FloatingPointError("fitted parameters cannot be represented in the input units")
    evaluation = evaluate_likelihood(
        model,
        scaled_parameters,
        optimization_design,
        response,
    )
    information = -evaluation.hessian
    positive_definite, condition_number = _information_diagnostics(information)
    scaled_covariance = _inverse_information(information)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        inverse_scales = 1.0 / column_scales
        covariance = scaled_covariance * np.outer(inverse_scales, inverse_scales)
    if not np.all(np.isfinite(covariance)):
        raise FloatingPointError("coefficient covariance cannot be represented in the input units")
    linear_predictor = optimization_design @ scaled_parameters
    fitted = expit(linear_predictor) if model == "logistic" else np.exp(linear_predictor)
    residuals = response - fitted
    residual_df = n_observations - n_parameters
    if model == "poisson":
        safe_mean = np.maximum(fitted, np.finfo(float).tiny)
        overdispersion = float(np.sum(residuals**2 / safe_mean) / residual_df)
    else:
        overdispersion = float("nan")
    overdispersion_detected = bool(model == "poisson" and overdispersion > 1.5)
    gradient_norm = float(np.linalg.norm(evaluation.score, ord=np.inf))
    average_gradient_norm = gradient_norm / n_observations
    average_gradient_tolerance = max(tolerance, np.sqrt(np.finfo(float).eps))
    numerically_converged = bool(average_gradient_norm <= average_gradient_tolerance)
    warnings: list[str] = []
    if not numerically_converged:
        warnings.append(f"optimizer did not converge: {optimization.message}")
    elif not optimization.success:
        warnings.append(
            "optimizer returned a non-success status, but the scaled score "
            "met the floating-point stationarity floor"
        )
    if not positive_definite:
        warnings.append("observed information is not numerically positive definite")
    if separation and model == "logistic":
        warnings.append(
            "complete or quasi-complete logistic separation detected; the finite MLE is not valid"
        )
    elif separation:
        warnings.append("Poisson zero-count separation detected; the finite MLE is not valid")
    if overdispersion_detected:
        warnings.append("Poisson Pearson dispersion exceeds 1.5; model-based SE may be too small")
    implemented_diagnostics_passed = bool(
        numerically_converged
        and positive_definite
        and not separation
        and not overdispersion_detected
    )
    diagnostics = MLEDiagnostics(
        optimizer_converged=numerically_converged,
        optimizer_status=int(optimization.status),
        optimizer_message=str(optimization.message),
        iterations=int(getattr(optimization, "nit", 0)),
        gradient_norm=gradient_norm,
        average_gradient_norm=average_gradient_norm,
        hessian_condition_number=condition_number,
        information_positive_definite=positive_definite,
        design_rank=rank,
        residual_degrees_of_freedom=residual_df,
        separation_detected=separation,
        overdispersion_ratio=overdispersion,
        overdispersion_detected=overdispersion_detected,
        implemented_diagnostics_passed=implemented_diagnostics_passed,
        warnings=tuple(warnings),
    )
    return MLEResult(
        model=model,
        parameters=parameters,
        coefficients=parameters.copy(),
        scale=1.0,
        covariance=covariance,
        standard_errors=np.sqrt(np.maximum(np.diag(covariance), 0.0)),
        fitted_mean=np.asarray(fitted, dtype=float),
        residuals=np.asarray(residuals, dtype=float),
        log_likelihood=evaluation.log_likelihood,
        n_observations=n_observations,
        diagnostics=diagnostics,
    )


def fit_logistic_mle(
    X: ArrayLike,
    y: ArrayLike,
    *,
    initial: ArrayLike | None = None,
    max_iterations: int = 500,
    gradient_tolerance: float = 1e-8,
) -> MLEResult:
    """Fit a Bernoulli logistic MLE and report complete or quasi separation."""

    return _fit_glm_mle(
        "logistic",
        X,
        y,
        initial=initial,
        max_iterations=max_iterations,
        gradient_tolerance=gradient_tolerance,
    )


def fit_poisson_mle(
    X: ArrayLike,
    y: ArrayLike,
    *,
    initial: ArrayLike | None = None,
    max_iterations: int = 500,
    gradient_tolerance: float = 1e-8,
) -> MLEResult:
    """Fit a Poisson log-linear MLE and report Pearson overdispersion."""

    return _fit_glm_mle(
        "poisson",
        X,
        y,
        initial=initial,
        max_iterations=max_iterations,
        gradient_tolerance=gradient_tolerance,
    )


@dataclass(frozen=True)
class HypothesisTestResult:
    """Chi-squared reference result for LR, Wald, or score tests."""

    statistic: float
    degrees_of_freedom: int
    p_value: float
    method: Literal["likelihood-ratio", "wald", "score"]


def _chi_squared_result(
    statistic: float,
    degrees_of_freedom: int,
    method: Literal["likelihood-ratio", "wald", "score"],
) -> HypothesisTestResult:
    value = float(statistic)
    if not np.isfinite(value) or value < 0.0:
        raise ValueError("test statistic must be finite and non-negative")
    degrees = _positive_integer(degrees_of_freedom, name="degrees_of_freedom")
    return HypothesisTestResult(
        statistic=value,
        degrees_of_freedom=degrees,
        p_value=float(chi2.sf(value, degrees)),
        method=method,
    )


def likelihood_ratio_test(
    full_log_likelihood: float,
    restricted_log_likelihood: float,
    degrees_of_freedom: int,
) -> HypothesisTestResult:
    """Compare nested likelihoods using the asymptotic chi-squared reference."""

    full = float(full_log_likelihood)
    restricted = float(restricted_log_likelihood)
    if not np.isfinite(full) or not np.isfinite(restricted):
        raise ValueError("log-likelihoods must be finite")
    difference = full - restricted
    tolerance = 100.0 * np.finfo(float).eps * max(1.0, abs(full), abs(restricted))
    if difference < -tolerance:
        raise ValueError("full log-likelihood must not be below restricted log-likelihood")
    return _chi_squared_result(
        2.0 * max(0.0, difference),
        degrees_of_freedom,
        "likelihood-ratio",
    )


def wald_test(
    estimate: ArrayLike,
    covariance: ArrayLike,
    contrast: ArrayLike,
    *,
    null: float | ArrayLike = 0.0,
) -> HypothesisTestResult:
    """Test ``contrast @ estimate = null`` with a Wald quadratic form."""

    coefficients = _vector(estimate, name="estimate")
    covariance_matrix = np.asarray(covariance, dtype=float)
    if covariance_matrix.shape != (coefficients.size, coefficients.size):
        raise ValueError("covariance must be square with one row per estimate")
    raw_contrast = np.asarray(contrast, dtype=float)
    matrix = raw_contrast[None, :] if raw_contrast.ndim == 1 else raw_contrast
    if matrix.ndim != 2 or matrix.shape[1] != coefficients.size or matrix.shape[0] < 1:
        raise ValueError("contrast must have one column per estimate")
    if not np.all(np.isfinite(covariance_matrix)) or not np.all(np.isfinite(matrix)):
        raise ValueError("covariance and contrast must contain only finite values")
    symmetry_tolerance = 100.0 * np.finfo(float).eps * float(np.max(np.abs(covariance_matrix)))
    if not np.allclose(
        covariance_matrix,
        covariance_matrix.T,
        rtol=0.0,
        atol=symmetry_tolerance,
    ):
        raise ValueError("covariance must be symmetric")
    covariance_matrix = 0.5 * (covariance_matrix + covariance_matrix.T)
    rank = int(np.linalg.matrix_rank(matrix))
    if rank != matrix.shape[0]:
        raise ValueError("contrast rows must be linearly independent")
    null_array = np.asarray(null, dtype=float)
    if null_array.ndim == 0:
        target = np.full(matrix.shape[0], float(null_array))
    elif null_array.shape == (matrix.shape[0],):
        target = null_array
    else:
        raise ValueError("null must be scalar or have one entry per contrast")
    if not np.all(np.isfinite(target)):
        raise ValueError("null must contain only finite values")
    difference = matrix @ coefficients - target
    contrast_covariance = matrix @ covariance_matrix @ matrix.T
    if np.linalg.matrix_rank(contrast_covariance) < rank:
        raise np.linalg.LinAlgError("contrast covariance is rank-deficient")
    if np.min(np.linalg.eigvalsh(contrast_covariance)) <= 0.0:
        raise np.linalg.LinAlgError("contrast covariance must be positive definite")
    statistic = float(difference @ np.linalg.solve(contrast_covariance, difference))
    return _chi_squared_result(statistic, rank, "wald")


def score_test(score: ArrayLike, information: ArrayLike) -> HypothesisTestResult:
    """Form a score test from a restricted score and Fisher information."""

    score_vector = _vector(score, name="score")
    information_matrix = np.asarray(information, dtype=float)
    if information_matrix.shape != (score_vector.size, score_vector.size):
        raise ValueError("information must be square with one row per score entry")
    if not np.all(np.isfinite(information_matrix)):
        raise ValueError("information must contain only finite values")
    symmetry_tolerance = 100.0 * np.finfo(float).eps * float(np.max(np.abs(information_matrix)))
    if not np.allclose(
        information_matrix,
        information_matrix.T,
        rtol=0.0,
        atol=symmetry_tolerance,
    ):
        raise ValueError("information must be symmetric")
    information_matrix = 0.5 * (information_matrix + information_matrix.T)
    if np.linalg.matrix_rank(information_matrix) < score_vector.size:
        raise np.linalg.LinAlgError("information is rank-deficient")
    if np.min(np.linalg.eigvalsh(information_matrix)) <= 0.0:
        raise np.linalg.LinAlgError("information must be positive definite")
    statistic = float(score_vector @ np.linalg.solve(information_matrix, score_vector))
    return _chi_squared_result(statistic, score_vector.size, "score")


@dataclass(frozen=True)
class CoverageSummary:
    """Finite-sample comparison of empirical dispersion and reported SE."""

    true_value: float
    empirical_bias: float
    empirical_standard_deviation: float
    mean_model_standard_error: float
    standard_error_ratio: float
    coverage: float
    coverage_monte_carlo_error: float
    confidence_level: float
    n_replications: int


def summarize_coverage(
    estimates: ArrayLike,
    standard_errors: ArrayLike,
    true_value: float,
    *,
    confidence_level: float = 0.95,
) -> CoverageSummary:
    """Summarize scalar-estimator bias, SE calibration, and Wald coverage."""

    point_estimates = _vector(estimates, name="estimates")
    model_errors = _vector(
        standard_errors,
        name="standard_errors",
        size=point_estimates.size,
    )
    if point_estimates.size < 2:
        raise ValueError("coverage requires at least two replications")
    if np.any(model_errors < 0.0):
        raise ValueError("standard_errors must be non-negative")
    target = float(true_value)
    if not np.isfinite(target):
        raise ValueError("true_value must be finite")
    level = _confidence_level(confidence_level)
    critical_value = NormalDist().inv_cdf((1.0 + level) / 2.0)
    covered = np.abs(point_estimates - target) <= critical_value * model_errors
    empirical_sd = float(point_estimates.std(ddof=1))
    mean_standard_error = float(model_errors.mean())
    coverage = float(covered.mean())
    ratio = mean_standard_error / empirical_sd if empirical_sd > 0.0 else float("nan")
    return CoverageSummary(
        true_value=target,
        empirical_bias=float(point_estimates.mean() - target),
        empirical_standard_deviation=empirical_sd,
        mean_model_standard_error=mean_standard_error,
        standard_error_ratio=float(ratio),
        coverage=coverage,
        coverage_monte_carlo_error=float(
            np.sqrt(coverage * (1.0 - coverage) / point_estimates.size)
        ),
        confidence_level=level,
        n_replications=point_estimates.size,
    )
