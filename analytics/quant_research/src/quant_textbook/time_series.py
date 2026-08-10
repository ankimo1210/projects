"""Transparent time-series primitives for the B7 Treasury chapters.

The routines deliberately expose fitted coefficients and diagnostics.  They
are instructional baselines, not a replacement for a production econometrics
package.  Input rows are assumed to be equally spaced *publication* times.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize, stats


def _series(values: object, *, name: str = "values", minimum: int = 3) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < minimum:
        raise ValueError(f"{name} must be one-dimensional with at least {minimum} values")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _matrix(values: object, *, name: str = "values", minimum: int = 3) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or min(array.shape) < 1 or array.shape[0] < minimum:
        raise ValueError(f"{name} must be a finite two-dimensional time-by-variable array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def autocorrelation(values: object, max_lag: int) -> np.ndarray:
    """Return the sample autocorrelation at lags ``0..max_lag``."""
    series = _series(values)
    if isinstance(max_lag, bool) or not isinstance(max_lag, int) or not 0 <= max_lag < series.size:
        raise ValueError("max_lag must be an integer between zero and n_observations - 1")
    centered = series - series.mean()
    denominator = float(centered @ centered)
    if denominator <= np.finfo(float).tiny:
        raise ValueError("autocorrelation is undefined for a constant series")
    return np.array(
        [
            1.0 if lag == 0 else float(centered[lag:] @ centered[:-lag]) / denominator
            for lag in range(max_lag + 1)
        ]
    )


def partial_autocorrelation(values: object, max_lag: int) -> np.ndarray:
    """Return Yule--Walker partial autocorrelations at lags ``0..max_lag``."""
    acf = autocorrelation(values, max_lag)
    result = np.ones(max_lag + 1)
    for lag in range(1, max_lag + 1):
        toeplitz = np.fromfunction(lambda i, j: acf[np.abs(i - j).astype(int)], (lag, lag))
        result[lag] = np.linalg.solve(toeplitz, acf[1 : lag + 1])[-1]
    return result


@dataclass(frozen=True)
class DickeyFullerDiagnostic:
    coefficient: float
    standard_error: float
    t_statistic: float
    n_observations: int
    includes_intercept: bool


def dickey_fuller_diagnostic(
    values: object, *, include_intercept: bool = True
) -> DickeyFullerDiagnostic:
    """Fit ``Δy_t = c + gamma y_{t-1} + e_t`` without a calibrated p-value.

    Dickey--Fuller critical values are non-standard.  The returned t statistic
    must not be interpreted using an ordinary Student-t reference law.
    """
    series = _series(values, minimum=8)
    if not isinstance(include_intercept, bool):
        raise TypeError("include_intercept must be bool")
    target = np.diff(series)
    lagged = series[:-1, None]
    design = np.column_stack([np.ones(target.size), lagged]) if include_intercept else lagged
    coefficients, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank != design.shape[1] or target.size <= design.shape[1]:
        raise ValueError("Dickey-Fuller regression is rank deficient")
    residuals = target - design @ coefficients
    q, r = np.linalg.qr(design, mode="reduced")
    del q
    r_inverse = np.linalg.solve(r, np.eye(r.shape[0]))
    covariance = (
        float(residuals @ residuals) / (target.size - design.shape[1]) * (r_inverse @ r_inverse.T)
    )
    index = 1 if include_intercept else 0
    standard_error = float(np.sqrt(covariance[index, index]))
    return DickeyFullerDiagnostic(
        coefficient=float(coefficients[index]),
        standard_error=standard_error,
        t_statistic=float(coefficients[index] / standard_error),
        n_observations=target.size,
        includes_intercept=include_intercept,
    )


@dataclass(frozen=True)
class ARModel:
    intercept: float
    coefficients: np.ndarray
    residual_variance: float
    n_observations: int
    condition_number: float


def fit_ar(values: object, order: int = 1, *, include_intercept: bool = True) -> ARModel:
    """Fit an AR model by least squares on publication-spaced observations."""
    series = _series(values, minimum=6)
    if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= series.size // 3:
        raise ValueError("order must be a positive integer no larger than n_observations // 3")
    if not isinstance(include_intercept, bool):
        raise TypeError("include_intercept must be bool")
    target = series[order:]
    lags = np.column_stack([series[order - lag - 1 : -lag - 1] for lag in range(order)])
    design = np.column_stack([np.ones(target.size), lags]) if include_intercept else lags
    coefficients, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank != design.shape[1]:
        raise ValueError("AR design is rank deficient")
    residuals = target - design @ coefficients
    degrees = target.size - design.shape[1]
    if degrees <= 0:
        raise ValueError("AR model has no residual degrees of freedom")
    intercept = float(coefficients[0]) if include_intercept else 0.0
    slopes = coefficients[1:] if include_intercept else coefficients
    return ARModel(
        intercept=intercept,
        coefficients=np.asarray(slopes, dtype=float),
        residual_variance=float(residuals @ residuals / degrees),
        n_observations=target.size,
        condition_number=float(np.linalg.cond(design)),
    )


def forecast_ar(model: ARModel, history: object, horizon: int) -> np.ndarray:
    """Iterate an AR model for ``horizon`` publication steps."""
    if not isinstance(model, ARModel):
        raise TypeError("model must be an ARModel")
    past = list(_series(history, minimum=model.coefficients.size)[-model.coefficients.size :])
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    forecasts: list[float] = []
    for _ in range(horizon):
        lag_vector = np.asarray(past[-model.coefficients.size :][::-1])
        value = model.intercept + float(model.coefficients @ lag_vector)
        forecasts.append(value)
        past.append(value)
    return np.asarray(forecasts)


@dataclass(frozen=True)
class VARModel:
    intercept: np.ndarray
    coefficient_matrices: np.ndarray
    residual_covariance: np.ndarray
    n_observations: int
    condition_number: float


def fit_var(values: object, lags: int = 1) -> VARModel:
    """Fit a reduced-form VAR with an intercept by multivariate least squares."""
    data = _matrix(values, minimum=8)
    if isinstance(lags, bool) or not isinstance(lags, int) or not 1 <= lags <= data.shape[0] // 4:
        raise ValueError("lags must be a positive integer no larger than n_observations // 4")
    target = data[lags:]
    lagged = np.column_stack([data[lags - lag - 1 : -lag - 1] for lag in range(lags)])
    design = np.column_stack([np.ones(target.shape[0]), lagged])
    coefficients, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank != design.shape[1]:
        raise ValueError("VAR design is rank deficient")
    residuals = target - design @ coefficients
    degrees = target.shape[0] - design.shape[1]
    if degrees <= 0:
        raise ValueError("VAR model has no residual degrees of freedom")
    dimension = data.shape[1]
    matrices = np.stack(
        [coefficients[1 + lag * dimension : 1 + (lag + 1) * dimension].T for lag in range(lags)]
    )
    return VARModel(
        intercept=np.asarray(coefficients[0], dtype=float),
        coefficient_matrices=matrices,
        residual_covariance=np.asarray(residuals.T @ residuals / degrees, dtype=float),
        n_observations=target.shape[0],
        condition_number=float(np.linalg.cond(design)),
    )


def forecast_var(model: VARModel, history: object, horizon: int) -> np.ndarray:
    """Iterate a fitted VAR and return ``(horizon, n_series)`` forecasts."""
    if not isinstance(model, VARModel):
        raise TypeError("model must be a VARModel")
    data = _matrix(history, minimum=model.coefficient_matrices.shape[0])
    if data.shape[1] != model.intercept.size:
        raise ValueError("history has the wrong number of variables")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    past = [row.copy() for row in data]
    forecasts: list[np.ndarray] = []
    for _ in range(horizon):
        value = model.intercept.copy()
        for lag, matrix in enumerate(model.coefficient_matrices, start=1):
            value += matrix @ past[-lag]
        forecasts.append(value.copy())
        past.append(value)
    return np.asarray(forecasts)


def impulse_response(model: VARModel, horizon: int, *, orthogonalized: bool = False) -> np.ndarray:
    """Return reduced-form or Cholesky-orthogonalized VAR impulse responses."""
    if not isinstance(model, VARModel):
        raise TypeError("model must be a VARModel")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("horizon must be a non-negative integer")
    dimension = model.intercept.size
    responses = np.zeros((horizon + 1, dimension, dimension))
    responses[0] = (
        np.linalg.cholesky(model.residual_covariance) if orthogonalized else np.eye(dimension)
    )
    for step in range(1, horizon + 1):
        for lag, matrix in enumerate(model.coefficient_matrices, start=1):
            if step - lag >= 0:
                responses[step] += matrix @ responses[step - lag]
    return responses


@dataclass(frozen=True)
class GrangerCausalityResult:
    f_statistic: float
    p_value: float
    numerator_degrees: int
    denominator_degrees: int


def granger_causality_test(effect: object, cause: object, lags: int = 1) -> GrangerCausalityResult:
    """Test whether lagged ``cause`` improves a linear forecast of ``effect``."""
    y = _series(effect, name="effect", minimum=12)
    x = _series(cause, name="cause", minimum=12)
    if y.size != x.size:
        raise ValueError("effect and cause must have the same length")
    if isinstance(lags, bool) or not isinstance(lags, int) or not 1 <= lags <= y.size // 5:
        raise ValueError("lags must be a positive integer no larger than n_observations // 5")
    target = y[lags:]
    y_lags = np.column_stack([y[lags - lag - 1 : -lag - 1] for lag in range(lags)])
    x_lags = np.column_stack([x[lags - lag - 1 : -lag - 1] for lag in range(lags)])
    restricted = np.column_stack([np.ones(target.size), y_lags])
    unrestricted = np.column_stack([restricted, x_lags])
    beta_r = np.linalg.lstsq(restricted, target, rcond=None)[0]
    beta_u, _, rank, _ = np.linalg.lstsq(unrestricted, target, rcond=None)
    if rank != unrestricted.shape[1]:
        raise ValueError("Granger regression is rank deficient")
    rss_r = float(np.sum((target - restricted @ beta_r) ** 2))
    rss_u = float(np.sum((target - unrestricted @ beta_u) ** 2))
    denominator_degrees = target.size - unrestricted.shape[1]
    statistic = max(0.0, (rss_r - rss_u) / lags) / (rss_u / denominator_degrees)
    return GrangerCausalityResult(
        f_statistic=float(statistic),
        p_value=float(stats.f.sf(statistic, lags, denominator_degrees)),
        numerator_degrees=lags,
        denominator_degrees=denominator_degrees,
    )


@dataclass(frozen=True)
class GARCH11Model:
    omega: float
    alpha: float
    beta: float
    conditional_variance: np.ndarray
    log_likelihood: float
    converged: bool
    n_iterations: int


def _garch_variance(values: np.ndarray, omega: float, alpha: float, beta: float) -> np.ndarray:
    variance = np.empty(values.size)
    variance[0] = max(float(np.var(values)), np.finfo(float).eps)
    for index in range(1, values.size):
        variance[index] = omega + alpha * values[index - 1] ** 2 + beta * variance[index - 1]
    return variance


def fit_garch11(values: object) -> GARCH11Model:
    """Fit a zero-mean Gaussian GARCH(1,1) with ``alpha + beta < 1``."""
    raw = _series(values, minimum=40)
    centered = raw - raw.mean()
    scale = float(np.sqrt(np.mean(centered**2)))
    if scale <= np.finfo(float).tiny:
        raise ValueError("GARCH requires non-constant observations")
    data = centered / scale

    def unpack(parameters: np.ndarray) -> tuple[float, float, float]:
        omega = float(np.exp(np.clip(parameters[0], -30.0, 20.0)))
        a = float(np.exp(np.clip(parameters[1], -30.0, 20.0)))
        b = float(np.exp(np.clip(parameters[2], -30.0, 20.0)))
        denominator = 1.0 + a + b
        return omega, 0.999 * a / denominator, 0.999 * b / denominator

    def objective(parameters: np.ndarray) -> float:
        omega, alpha, beta = unpack(parameters)
        variance = _garch_variance(data, omega, alpha, beta)
        return float(0.5 * np.sum(np.log(2.0 * np.pi * variance) + data**2 / variance))

    initial = np.array([np.log(0.03), np.log(0.08), np.log(0.88)])
    result = optimize.minimize(objective, initial, method="L-BFGS-B", options={"maxiter": 2000})
    omega_scaled, alpha, beta = unpack(np.asarray(result.x))
    variance = _garch_variance(data, omega_scaled, alpha, beta) * scale**2
    return GARCH11Model(
        omega=float(omega_scaled * scale**2),
        alpha=alpha,
        beta=beta,
        conditional_variance=variance,
        log_likelihood=float(-objective(np.asarray(result.x)) - raw.size * np.log(scale)),
        converged=bool(result.success),
        n_iterations=int(result.nit),
    )


def forecast_garch_variance(
    model: GARCH11Model, last_observation: float, horizon: int
) -> np.ndarray:
    """Forecast conditional variance recursively from the last fitted state."""
    if not isinstance(model, GARCH11Model):
        raise TypeError("model must be a GARCH11Model")
    if not np.isfinite(last_observation):
        raise ValueError("last_observation must be finite")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    result = np.empty(horizon)
    previous_variance = float(model.conditional_variance[-1])
    previous_squared = float(last_observation) ** 2
    for index in range(horizon):
        previous_variance = (
            model.omega + model.alpha * previous_squared + model.beta * previous_variance
        )
        result[index] = previous_variance
        previous_squared = previous_variance
    return result


__all__ = [
    "ARModel",
    "DickeyFullerDiagnostic",
    "GARCH11Model",
    "GrangerCausalityResult",
    "VARModel",
    "autocorrelation",
    "dickey_fuller_diagnostic",
    "fit_ar",
    "fit_garch11",
    "fit_var",
    "forecast_ar",
    "forecast_garch_variance",
    "forecast_var",
    "granger_causality_test",
    "impulse_response",
    "partial_autocorrelation",
]
