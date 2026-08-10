"""Linear-Gaussian state-space and Dynamic Nelson--Siegel helpers for B7."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _finite_matrix(values: object, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or min(array.shape) < 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a non-empty finite matrix")
    return array


def _symmetric(values: object, *, name: str, size: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (size, size) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite ({size}, {size}) matrix")
    scale = max(float(np.max(np.abs(array))), np.finfo(float).tiny)
    if np.max(np.abs(array - array.T)) > 100.0 * np.finfo(float).eps * scale:
        raise ValueError(f"{name} must be symmetric")
    array = 0.5 * (array + array.T)
    if np.linalg.eigvalsh(array).min() < -100.0 * np.finfo(float).eps * scale * size:
        raise ValueError(f"{name} must be positive semidefinite")
    return array


@dataclass(frozen=True)
class KalmanFilterResult:
    predicted_means: np.ndarray
    predicted_covariances: np.ndarray
    filtered_means: np.ndarray
    filtered_covariances: np.ndarray
    innovations: np.ndarray
    innovation_variances: np.ndarray
    observed_mask: np.ndarray
    log_likelihood: float


@dataclass(frozen=True)
class KalmanSmootherResult:
    smoothed_means: np.ndarray
    smoothed_covariances: np.ndarray


def kalman_filter(
    observations: object,
    transition: object,
    observation_matrix: object,
    process_covariance: object,
    observation_covariance: object,
    initial_mean: object,
    initial_covariance: object,
    *,
    transition_intercept: object | None = None,
) -> KalmanFilterResult:
    """Run a missing-observation-aware linear Gaussian Kalman filter."""
    observed = np.asarray(observations, dtype=float)
    if observed.ndim == 1:
        observed = observed[:, None]
    if observed.ndim != 2 or observed.shape[0] < 1 or np.any(np.isinf(observed)):
        raise ValueError(
            "observations must be a time-by-observation array with finite values or NaN"
        )
    f = _finite_matrix(transition, name="transition")
    h = _finite_matrix(observation_matrix, name="observation_matrix")
    state_size = f.shape[0]
    if f.shape[1] != state_size or h.shape != (observed.shape[1], state_size):
        raise ValueError("transition or observation_matrix has an incompatible shape")
    q = _symmetric(process_covariance, name="process_covariance", size=state_size)
    r = _symmetric(observation_covariance, name="observation_covariance", size=observed.shape[1])
    mean = np.asarray(initial_mean, dtype=float)
    if mean.shape != (state_size,) or not np.all(np.isfinite(mean)):
        raise ValueError("initial_mean has an incompatible shape or non-finite value")
    covariance = _symmetric(initial_covariance, name="initial_covariance", size=state_size)
    intercept = (
        np.zeros(state_size)
        if transition_intercept is None
        else np.asarray(transition_intercept, dtype=float)
    )
    if intercept.shape != (state_size,) or not np.all(np.isfinite(intercept)):
        raise ValueError("transition_intercept has an incompatible shape or non-finite value")

    n_times, observation_size = observed.shape
    predicted_means = np.empty((n_times, state_size))
    predicted_covariances = np.empty((n_times, state_size, state_size))
    filtered_means = np.empty_like(predicted_means)
    filtered_covariances = np.empty_like(predicted_covariances)
    innovations = np.full((n_times, observation_size), np.nan)
    innovation_variances = np.full((n_times, observation_size, observation_size), np.nan)
    mask_table = np.isfinite(observed)
    log_likelihood = 0.0
    identity = np.eye(state_size)

    for time in range(n_times):
        if time == 0:
            predicted_mean = mean
            predicted_covariance = covariance
        else:
            predicted_mean = intercept + f @ filtered_means[time - 1]
            predicted_covariance = f @ filtered_covariances[time - 1] @ f.T + q
        predicted_covariance = 0.5 * (predicted_covariance + predicted_covariance.T)
        predicted_means[time] = predicted_mean
        predicted_covariances[time] = predicted_covariance

        mask = mask_table[time]
        if not np.any(mask):
            filtered_means[time] = predicted_mean
            filtered_covariances[time] = predicted_covariance
            continue
        selected_h = h[mask]
        selected_r = r[np.ix_(mask, mask)]
        innovation = observed[time, mask] - selected_h @ predicted_mean
        innovation_covariance = selected_h @ predicted_covariance @ selected_h.T + selected_r
        sign, log_determinant = np.linalg.slogdet(innovation_covariance)
        if sign <= 0:
            raise ValueError("innovation covariance is not positive definite")
        gain = np.linalg.solve(innovation_covariance, selected_h @ predicted_covariance).T
        filtered_mean = predicted_mean + gain @ innovation
        update = identity - gain @ selected_h
        filtered_covariance = update @ predicted_covariance @ update.T + gain @ selected_r @ gain.T
        filtered_covariance = 0.5 * (filtered_covariance + filtered_covariance.T)
        filtered_means[time] = filtered_mean
        filtered_covariances[time] = filtered_covariance
        innovations[time, mask] = innovation
        innovation_variances[time][np.ix_(mask, mask)] = innovation_covariance
        quadratic = float(innovation @ np.linalg.solve(innovation_covariance, innovation))
        log_likelihood += -0.5 * (mask.sum() * np.log(2.0 * np.pi) + log_determinant + quadratic)

    return KalmanFilterResult(
        predicted_means=predicted_means,
        predicted_covariances=predicted_covariances,
        filtered_means=filtered_means,
        filtered_covariances=filtered_covariances,
        innovations=innovations,
        innovation_variances=innovation_variances,
        observed_mask=mask_table,
        log_likelihood=float(log_likelihood),
    )


def kalman_smoother(result: KalmanFilterResult, transition: object) -> KalmanSmootherResult:
    """Run the Rauch--Tung--Striebel backward smoother."""
    if not isinstance(result, KalmanFilterResult):
        raise TypeError("result must be a KalmanFilterResult")
    f = _finite_matrix(transition, name="transition")
    state_size = result.filtered_means.shape[1]
    if f.shape != (state_size, state_size):
        raise ValueError("transition has an incompatible shape")
    means = result.filtered_means.copy()
    covariances = result.filtered_covariances.copy()
    for time in range(means.shape[0] - 2, -1, -1):
        gain = np.linalg.solve(
            result.predicted_covariances[time + 1],
            f @ result.filtered_covariances[time],
        ).T
        means[time] += gain @ (means[time + 1] - result.predicted_means[time + 1])
        covariances[time] += (
            gain @ (covariances[time + 1] - result.predicted_covariances[time + 1]) @ gain.T
        )
        covariances[time] = 0.5 * (covariances[time] + covariances[time].T)
    return KalmanSmootherResult(smoothed_means=means, smoothed_covariances=covariances)


def nelson_siegel_loadings(maturities: object, decay: float) -> np.ndarray:
    """Return level, slope, and curvature loadings for maturities in years."""
    values = np.asarray(maturities, dtype=float)
    if (
        values.ndim != 1
        or values.size < 3
        or not np.all(np.isfinite(values))
        or np.any(values <= 0.0)
    ):
        raise ValueError("maturities must contain at least three finite positive values")
    if not np.isfinite(decay) or decay <= 0.0:
        raise ValueError("decay must be strictly positive")
    scaled = decay * values
    slope = -np.expm1(-scaled) / scaled
    return np.column_stack([np.ones(values.size), slope, slope - np.exp(-scaled)])


def extract_nelson_siegel_factors(yields: object, maturities: object, decay: float) -> np.ndarray:
    """Estimate fixed-decay Nelson--Siegel factors independently by date."""
    data = _finite_matrix(yields, name="yields")
    loadings = nelson_siegel_loadings(maturities, decay)
    if data.shape[1] != loadings.shape[0]:
        raise ValueError("yields and maturities have incompatible shapes")
    factors, _, rank, _ = np.linalg.lstsq(loadings, data.T, rcond=None)
    if rank != 3:
        raise ValueError("Nelson-Siegel loading matrix is rank deficient")
    return factors.T


@dataclass(frozen=True)
class DynamicNelsonSiegelModel:
    maturities: np.ndarray
    decay: float
    loadings: np.ndarray
    transition: np.ndarray
    transition_intercept: np.ndarray
    process_covariance: np.ndarray
    observation_covariance: np.ndarray
    initial_mean: np.ndarray
    initial_covariance: np.ndarray
    training_observations: int


@dataclass(frozen=True)
class PredictiveCurve:
    mean: np.ndarray
    covariance: np.ndarray
    horizon_publications: int


def fit_dynamic_nelson_siegel(
    yields: object, maturities: object, *, decay: float
) -> DynamicNelsonSiegelModel:
    """Fit fixed-decay DNS by two-step cross-sectional OLS and factor VAR(1)."""
    data = _finite_matrix(yields, name="yields")
    if data.shape[0] < 30:
        raise ValueError("Dynamic Nelson-Siegel requires at least 30 observations")
    loadings = nelson_siegel_loadings(maturities, decay)
    factors = extract_nelson_siegel_factors(data, maturities, decay)
    design = np.column_stack([np.ones(factors.shape[0] - 1), factors[:-1]])
    coefficients, _, rank, _ = np.linalg.lstsq(design, factors[1:], rcond=None)
    if rank != design.shape[1]:
        raise ValueError("factor transition design is rank deficient")
    transition_intercept = coefficients[0]
    transition = coefficients[1:].T
    transition_residuals = factors[1:] - design @ coefficients
    curve_residuals = data - factors @ loadings.T
    process_covariance = np.cov(transition_residuals, rowvar=False, ddof=1)
    observation_variance = np.maximum(np.var(curve_residuals, axis=0, ddof=1), 1e-10)
    process_covariance += np.eye(3) * max(float(np.trace(process_covariance)), 1.0) * 1e-10
    return DynamicNelsonSiegelModel(
        maturities=np.asarray(maturities, dtype=float),
        decay=float(decay),
        loadings=loadings,
        transition=transition,
        transition_intercept=np.asarray(transition_intercept),
        process_covariance=np.asarray(process_covariance),
        observation_covariance=np.diag(observation_variance),
        initial_mean=np.asarray(factors[0]),
        initial_covariance=np.cov(factors, rowvar=False, ddof=1),
        training_observations=data.shape[0],
    )


def filter_dynamic_nelson_siegel(
    model: DynamicNelsonSiegelModel, yields: object
) -> KalmanFilterResult:
    """Filter a yield panel under a fitted DNS parameter contract."""
    if not isinstance(model, DynamicNelsonSiegelModel):
        raise TypeError("model must be a DynamicNelsonSiegelModel")
    return kalman_filter(
        yields,
        model.transition,
        model.loadings,
        model.process_covariance,
        model.observation_covariance,
        model.initial_mean,
        model.initial_covariance,
        transition_intercept=model.transition_intercept,
    )


def forecast_dynamic_nelson_siegel(
    model: DynamicNelsonSiegelModel,
    filtered_mean: object,
    filtered_covariance: object,
    horizon_publications: int,
) -> PredictiveCurve:
    """Forecast the curve using only a filtered state at the forecast origin."""
    if not isinstance(model, DynamicNelsonSiegelModel):
        raise TypeError("model must be a DynamicNelsonSiegelModel")
    mean = np.asarray(filtered_mean, dtype=float)
    covariance = np.asarray(filtered_covariance, dtype=float)
    if mean.shape != (3,) or covariance.shape != (3, 3) or not np.all(np.isfinite(mean)):
        raise ValueError("filtered state has an incompatible shape or non-finite value")
    if (
        isinstance(horizon_publications, bool)
        or not isinstance(horizon_publications, int)
        or horizon_publications < 1
    ):
        raise ValueError("horizon_publications must be a positive integer")
    for _ in range(horizon_publications):
        mean = model.transition_intercept + model.transition @ mean
        covariance = model.transition @ covariance @ model.transition.T + model.process_covariance
    curve_mean = model.loadings @ mean
    curve_covariance = model.loadings @ covariance @ model.loadings.T + model.observation_covariance
    return PredictiveCurve(
        mean=curve_mean,
        covariance=0.5 * (curve_covariance + curve_covariance.T),
        horizon_publications=horizon_publications,
    )


__all__ = [
    "DynamicNelsonSiegelModel",
    "KalmanFilterResult",
    "KalmanSmootherResult",
    "PredictiveCurve",
    "extract_nelson_siegel_factors",
    "filter_dynamic_nelson_siegel",
    "fit_dynamic_nelson_siegel",
    "forecast_dynamic_nelson_siegel",
    "kalman_filter",
    "kalman_smoother",
    "nelson_siegel_loadings",
]
