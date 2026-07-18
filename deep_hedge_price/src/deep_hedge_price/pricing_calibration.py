"""Multi-start calibration adapters for analytic teachers and surrogates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

ForwardModel = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class CalibrationStart:
    """One optimizer start: initial point, solution, RMSE, and evaluation count."""

    initial: np.ndarray
    parameters: np.ndarray
    repricing_rmse: float
    success: bool
    evaluations: int


@dataclass(frozen=True)
class CalibrationResult:
    """Best multi-start calibration with per-start results and dispersion."""

    parameters: np.ndarray
    repricing_rmse: float
    starts: tuple[CalibrationStart, ...]
    parameter_dispersion: np.ndarray


@dataclass(frozen=True)
class DirectInverseRidge:
    """Linear direct-inverse ablation; forward calibration remains primary."""

    feature_mean: np.ndarray
    feature_scale: np.ndarray
    intercept: np.ndarray
    coefficients: np.ndarray

    def predict(self, surface_features: np.ndarray) -> np.ndarray:
        """Map normalized surface features to model parameters."""
        features = np.asarray(surface_features, dtype=float)
        if features.ndim != 2 or features.shape[1] != self.feature_mean.size:
            raise ValueError("surface_features must match the fitted feature dimension")
        if np.any(~np.isfinite(features)):
            raise ValueError("surface_features must be finite")
        normalized = (features - self.feature_mean) / self.feature_scale
        return self.intercept + normalized @ self.coefficients


def _finite_vector(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0 or np.any(~np.isfinite(array)):
        raise ValueError(f"{name} must be a non-empty finite one-dimensional array")
    return array


def calibrate_parameters(
    forward: ForwardModel,
    targets: np.ndarray,
    initial: np.ndarray,
    bounds: tuple[np.ndarray, np.ndarray],
    *,
    n_starts: int = 5,
    seed: int = 0,
    weights: np.ndarray | None = None,
) -> CalibrationResult:
    """Fit a forward teacher/surrogate and retain initial-value sensitivity."""
    targets = _finite_vector(targets, "targets")
    initial = _finite_vector(initial, "initial")
    lower, upper = (_finite_vector(bound, "bounds") for bound in bounds)
    if lower.shape != initial.shape or upper.shape != initial.shape:
        raise ValueError("bounds must match initial")
    if np.any(lower >= upper) or np.any(initial < lower) or np.any(initial > upper):
        raise ValueError("invalid bounds or initial point")
    if n_starts < 1:
        raise ValueError("n_starts must be positive")
    supplied_weights = (
        np.ones_like(targets) if weights is None else np.asarray(weights, dtype=float)
    )
    if (
        supplied_weights.shape != targets.shape
        or np.any(~np.isfinite(supplied_weights))
        or np.any(supplied_weights < 0)
    ):
        raise ValueError("weights must be non-negative and match targets")
    scale = np.sqrt(supplied_weights)

    def residual(parameters: np.ndarray) -> np.ndarray:
        fitted = np.asarray(forward(parameters), dtype=float)
        if fitted.shape != targets.shape:
            raise ValueError("forward model output must match targets")
        if np.any(~np.isfinite(fitted)):
            raise ValueError("forward model output must be finite")
        return (fitted - targets) * scale

    residual(initial)

    rng = np.random.default_rng(seed)
    initials = [initial]
    initials.extend(rng.uniform(lower, upper) for _ in range(n_starts - 1))
    starts: list[CalibrationStart] = []
    for point in initials:
        result = least_squares(
            residual,
            point,
            bounds=(lower, upper),
            max_nfev=2_000,
        )
        fitted = np.asarray(forward(result.x), dtype=float)
        starts.append(
            CalibrationStart(
                initial=np.asarray(point).copy(),
                parameters=np.asarray(result.x).copy(),
                repricing_rmse=float(np.sqrt(np.mean((fitted - targets) ** 2))),
                success=bool(result.success),
                evaluations=int(result.nfev),
            )
        )
    successful = [item for item in starts if item.success and np.isfinite(item.repricing_rmse)]
    if not successful:
        raise RuntimeError("all calibration starts failed")
    best = min(successful, key=lambda item: item.repricing_rmse)
    matrix = np.stack([item.parameters for item in starts])
    return CalibrationResult(
        parameters=best.parameters,
        repricing_rmse=best.repricing_rmse,
        starts=tuple(starts),
        parameter_dispersion=np.std(matrix, axis=0),
    )


def calibration_error_metrics(
    result: CalibrationResult,
    true_parameters: np.ndarray,
) -> dict[str, float]:
    """Keep parameter recovery error separate from quote repricing error."""

    truth = _finite_vector(true_parameters, "true_parameters")
    if truth.shape != result.parameters.shape:
        raise ValueError("true_parameters must match calibrated parameters")
    error = result.parameters - truth
    return {
        "repricing_rmse": float(result.repricing_rmse),
        "parameter_rmse": float(np.sqrt(np.mean(error**2))),
        "parameter_mae": float(np.mean(np.abs(error))),
        "parameter_max_abs_error": float(np.max(np.abs(error))),
    }


def fit_direct_inverse_ridge(
    surface_features: np.ndarray,
    parameters: np.ndarray,
    *,
    ridge: float = 1e-4,
) -> DirectInverseRidge:
    """Fit a direct surface-to-parameter map for ablation only."""

    features = np.asarray(surface_features, dtype=float)
    targets = np.asarray(parameters, dtype=float)
    if (
        features.ndim != 2
        or targets.ndim != 2
        or len(features) != len(targets)
        or len(features) < 2
        or np.any(~np.isfinite(features))
        or np.any(~np.isfinite(targets))
        or not np.isfinite(ridge)
        or ridge < 0.0
    ):
        raise ValueError(
            "direct inverse data must be aligned finite matrices and ridge non-negative"
        )
    mean = features.mean(axis=0)
    scale = features.std(axis=0)
    scale = np.where(scale > 0.0, scale, 1.0)
    normalized = (features - mean) / scale
    design = np.column_stack([np.ones(len(features)), normalized])
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
    return DirectInverseRidge(
        feature_mean=mean,
        feature_scale=scale,
        intercept=coefficients[0],
        coefficients=coefficients[1:],
    )


def compare_forward_models(
    teacher: ForwardModel,
    surrogate: ForwardModel,
    parameters: np.ndarray,
) -> dict[str, float]:
    """Report teacher/surrogate discrepancy without hiding teacher values."""
    expected = np.asarray(teacher(np.asarray(parameters, dtype=float)), dtype=float)
    observed = np.asarray(surrogate(np.asarray(parameters, dtype=float)), dtype=float)
    if expected.shape != observed.shape or expected.size == 0:
        raise ValueError("teacher and surrogate outputs must have matching shapes")
    if np.any(~np.isfinite(expected)) or np.any(~np.isfinite(observed)):
        raise ValueError("teacher and surrogate outputs must be finite")
    error = observed - expected
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "max_abs_error": float(np.max(np.abs(error))),
    }
