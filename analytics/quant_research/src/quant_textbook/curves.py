"""Yield-curve basis functions, fitting, prediction, and validation metrics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .numerics import (
    LeastSquaresDiagnostics,
    LeastSquaresMethod,
    LeastSquaresResult,
    solve_least_squares,
)

FloatArray = NDArray[np.float64]
CurveBasis = Literal["polynomial", "cubic_spline", "nelson_siegel"]


def _vector(values: ArrayLike, *, name: str, allow_zero: bool = True) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    lower_bound = 0.0 if allow_zero else np.nextafter(0.0, 1.0)
    if np.any(array < lower_bound):
        qualifier = "non-negative" if allow_zero else "strictly positive"
        raise ValueError(f"{name} must be {qualifier}")
    return array


def _normalization(location: float, scale: float) -> tuple[float, float]:
    if not np.isfinite(location):
        raise ValueError("location must be finite")
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("scale must be finite and strictly positive")
    return float(location), float(scale)


def polynomial_basis(
    maturities: ArrayLike,
    degree: int,
    *,
    location: float = 0.0,
    scale: float = 1.0,
) -> FloatArray:
    """Evaluate powers ``1, z, ..., z**degree`` for normalized maturity ``z``."""

    tenor = _vector(maturities, name="maturities")
    if isinstance(degree, bool) or not isinstance(degree, (int, np.integer)):
        raise TypeError("degree must be an integer")
    if degree < 0:
        raise ValueError("degree must be non-negative")
    location, scale = _normalization(location, scale)
    normalized = (tenor - location) / scale
    return np.vander(normalized, N=int(degree) + 1, increasing=True)


def truncated_power_cubic_spline_basis(
    maturities: ArrayLike,
    knots: Sequence[float] = (),
    *,
    location: float = 0.0,
    scale: float = 1.0,
) -> FloatArray:
    """Evaluate a cubic truncated-power basis.

    The columns are ``1, z, z**2, z**3`` followed by
    ``max(z-k, 0)**3`` for each knot.  Knots are supplied in maturity units
    and normalized with the same location and scale as observations.
    """

    tenor = _vector(maturities, name="maturities")
    location, scale = _normalization(location, scale)
    knot_array = np.asarray(knots, dtype=float)
    if knot_array.ndim != 1:
        raise ValueError("knots must be a one-dimensional sequence")
    if knot_array.size and (
        not np.all(np.isfinite(knot_array))
        or np.any(knot_array < 0.0)
        or np.any(np.diff(knot_array) <= 0.0)
    ):
        raise ValueError("knots must be finite, non-negative, and strictly increasing")
    normalized = (tenor - location) / scale
    normalized_knots = (knot_array - location) / scale
    polynomial = np.column_stack((np.ones(tenor.size), normalized, normalized**2, normalized**3))
    if not normalized_knots.size:
        return polynomial
    truncated = np.maximum(normalized[:, None] - normalized_knots[None, :], 0.0) ** 3
    return np.column_stack((polynomial, truncated))


def nelson_siegel_basis(maturities: ArrayLike, decay: float) -> FloatArray:
    r"""Evaluate the fixed-decay Nelson--Siegel yield basis.

    ``decay`` is :math:`\lambda > 0`, so the exponential term is
    :math:`\exp(-\lambda T)`.  The implementation uses ``expm1`` and has the
    correct limiting values at maturity zero.
    """

    tenor = _vector(maturities, name="maturities")
    if not np.isfinite(decay) or decay <= 0.0:
        raise ValueError("decay must be finite and strictly positive")
    scaled = float(decay) * tenor
    slope = np.divide(
        -np.expm1(-scaled),
        scaled,
        out=np.ones_like(scaled),
        where=scaled != 0.0,
    )
    curvature = slope - np.exp(-scaled)
    return np.column_stack((np.ones(tenor.size), slope, curvature))


@dataclass(frozen=True)
class CurveBasisSpec:
    """Parameters required to evaluate a fitted curve basis consistently."""

    basis: CurveBasis
    degree: int
    knots: tuple[float, ...]
    decay: float
    location: float
    scale: float


@dataclass(frozen=True)
class CurveFit:
    """A fitted yield curve and its observed cross-section."""

    basis_spec: CurveBasisSpec
    coefficients: FloatArray
    maturities: FloatArray
    observed_yields: FloatArray
    fitted_yields: FloatArray
    weights: FloatArray | None
    least_squares: LeastSquaresResult

    @property
    def basis(self) -> CurveBasis:
        """Canonical basis name."""

        return self.basis_spec.basis

    @property
    def decay(self) -> float:
        """Fixed Nelson--Siegel decay (stored for every basis)."""

        return self.basis_spec.decay

    @property
    def diagnostics(self) -> LeastSquaresDiagnostics:
        """Least-squares diagnostics for the curve design matrix."""

        return self.least_squares.diagnostics

    @property
    def fitted_values(self) -> FloatArray:
        """Alias used by the generic regression examples."""

        return self.fitted_yields

    @property
    def residuals(self) -> FloatArray:
        """Observed minus fitted yields."""

        return self.observed_yields - self.fitted_yields

    @property
    def in_sample_rmse(self) -> float:
        """Unweighted in-sample root mean squared error."""

        return rmse(self.observed_yields, self.fitted_yields)


def _canonical_basis_name(basis: str) -> CurveBasis:
    aliases = {
        "polynomial": "polynomial",
        "cubic_spline": "cubic_spline",
        "spline": "cubic_spline",
        "truncated_power": "cubic_spline",
        "nelson_siegel": "nelson_siegel",
        "ns": "nelson_siegel",
    }
    try:
        return aliases[basis]  # type: ignore[return-value]
    except KeyError as exc:
        raise ValueError(f"unknown curve basis: {basis!r}") from exc


def _basis_matrix(maturities: FloatArray, spec: CurveBasisSpec) -> FloatArray:
    if spec.basis == "polynomial":
        return polynomial_basis(maturities, spec.degree, location=spec.location, scale=spec.scale)
    if spec.basis == "cubic_spline":
        return truncated_power_cubic_spline_basis(
            maturities, spec.knots, location=spec.location, scale=spec.scale
        )
    return nelson_siegel_basis(maturities, spec.decay)


def _curve_spec(
    maturities: FloatArray,
    *,
    basis: str,
    degree: int,
    knots: Sequence[float],
    decay: float,
) -> CurveBasisSpec:
    canonical_basis = _canonical_basis_name(basis)
    maturity_range = float(np.ptp(maturities))
    if maturity_range == 0.0:
        raise ValueError("curve fitting requires at least two distinct maturities")
    location = float(maturities.min())
    scale = maturity_range
    knot_tuple = tuple(float(value) for value in knots)
    # Calling the public functions here also centralizes argument validation.
    spec = CurveBasisSpec(
        basis=canonical_basis,
        degree=degree,
        knots=knot_tuple,
        decay=float(decay),
        location=location,
        scale=scale,
    )
    _basis_matrix(maturities, spec)
    return spec


def fit_curve(
    maturities: ArrayLike,
    yields: ArrayLike,
    *,
    basis: str = "nelson_siegel",
    degree: int = 3,
    knots: Sequence[float] = (),
    decay: float = 0.5,
    weights: ArrayLike | None = None,
    ridge: float = 0.0,
    method: LeastSquaresMethod = "svd",
) -> CurveFit:
    """Fit yields directly in a chosen cross-sectional basis.

    This function is intentionally a *yield fit*.  Coupon-bond prices require
    discounting every cash flow and are handled by :mod:`quant_textbook.bonds`.
    """

    tenor = _vector(maturities, name="maturities")
    observed = np.asarray(yields, dtype=float)
    if observed.ndim != 1 or observed.shape != tenor.shape:
        raise ValueError("yields must be one-dimensional with one value per maturity")
    if not np.all(np.isfinite(observed)):
        raise ValueError("yields must contain only finite values")
    if np.unique(tenor).size != tenor.size:
        raise ValueError("maturities must be unique")
    spec = _curve_spec(tenor, basis=basis, degree=degree, knots=knots, decay=decay)
    design = _basis_matrix(tenor, spec)
    fit = solve_least_squares(design, observed, method=method, weights=weights, ridge=ridge)
    stored_weights = None if weights is None else np.asarray(weights, dtype=float).copy()
    return CurveFit(
        basis_spec=spec,
        coefficients=fit.coefficients,
        maturities=tenor.copy(),
        observed_yields=observed.copy(),
        fitted_yields=fit.fitted_values,
        weights=stored_weights,
        least_squares=fit,
    )


def predict_curve(model: CurveFit, maturities: ArrayLike) -> FloatArray:
    """Predict yields using the normalization and basis stored in ``model``."""

    if not isinstance(model, CurveFit):
        raise TypeError("model must be a CurveFit")
    tenor = _vector(maturities, name="maturities")
    return _basis_matrix(tenor, model.basis_spec) @ model.coefficients


def _metric_arrays(actual: ArrayLike, predicted: ArrayLike) -> tuple[FloatArray, FloatArray]:
    observed = np.asarray(actual, dtype=float)
    fitted = np.asarray(predicted, dtype=float)
    if observed.ndim != 1 or fitted.ndim != 1 or observed.size == 0:
        raise ValueError("actual and predicted must be non-empty one-dimensional arrays")
    if observed.shape != fitted.shape:
        raise ValueError("actual and predicted must have the same shape")
    if not np.all(np.isfinite(observed)) or not np.all(np.isfinite(fitted)):
        raise ValueError("metric inputs must contain only finite values")
    return observed, fitted


def rmse(actual: ArrayLike, predicted: ArrayLike) -> float:
    """Return root mean squared error."""

    observed, fitted = _metric_arrays(actual, predicted)
    return float(np.sqrt(np.mean((observed - fitted) ** 2)))


def weighted_rmse(actual: ArrayLike, predicted: ArrayLike, weights: ArrayLike) -> float:
    """Return root weighted mean squared error with normalized weights."""

    observed, fitted = _metric_arrays(actual, predicted)
    metric_weights = np.asarray(weights, dtype=float)
    if metric_weights.ndim != 1 or metric_weights.shape != observed.shape:
        raise ValueError("weights must have the same one-dimensional shape as actual")
    if not np.all(np.isfinite(metric_weights)) or np.any(metric_weights < 0.0):
        raise ValueError("weights must be finite and non-negative")
    if metric_weights.sum() <= 0.0:
        raise ValueError("at least one weight must be positive")
    return float(np.sqrt(np.average((observed - fitted) ** 2, weights=metric_weights)))


def leave_one_out_predictions(
    maturities: ArrayLike,
    yields: ArrayLike,
    *,
    basis: str = "nelson_siegel",
    degree: int = 3,
    knots: Sequence[float] = (),
    decay: float = 0.5,
    weights: ArrayLike | None = None,
    ridge: float = 0.0,
    method: LeastSquaresMethod = "svd",
) -> FloatArray:
    """Fit each curve with one tenor held out and return held-out predictions."""

    tenor = _vector(maturities, name="maturities")
    observed = np.asarray(yields, dtype=float)
    if observed.ndim != 1 or observed.shape != tenor.shape:
        raise ValueError("yields must be one-dimensional with one value per maturity")
    if tenor.size < 3:
        raise ValueError("leave-one-out validation requires at least three maturities")
    all_weights: FloatArray | None = None
    if weights is not None:
        all_weights = np.asarray(weights, dtype=float)
        if all_weights.ndim != 1 or all_weights.shape != tenor.shape:
            raise ValueError("weights must have one value per maturity")
        if not np.all(np.isfinite(all_weights)) or np.any(all_weights <= 0.0):
            raise ValueError("leave-one-out fitting weights must be finite and strictly positive")

    predictions = np.empty_like(observed)
    for held_out in range(tenor.size):
        training = np.arange(tenor.size) != held_out
        training_weights = None if all_weights is None else all_weights[training]
        model = fit_curve(
            tenor[training],
            observed[training],
            basis=basis,
            degree=degree,
            knots=knots,
            decay=decay,
            weights=training_weights,
            ridge=ridge,
            method=method,
        )
        predictions[held_out] = predict_curve(model, tenor[[held_out]])[0]
    return predictions


def leave_one_out_rmse(
    maturities: ArrayLike,
    yields: ArrayLike,
    *,
    basis: str = "nelson_siegel",
    degree: int = 3,
    knots: Sequence[float] = (),
    decay: float = 0.5,
    weights: ArrayLike | None = None,
    ridge: float = 0.0,
    method: LeastSquaresMethod = "svd",
) -> float:
    """Return tenor-wise leave-one-out RMSE (weighted when weights are given)."""

    predictions = leave_one_out_predictions(
        maturities,
        yields,
        basis=basis,
        degree=degree,
        knots=knots,
        decay=decay,
        weights=weights,
        ridge=ridge,
        method=method,
    )
    if weights is None:
        return rmse(yields, predictions)
    return weighted_rmse(yields, predictions, weights)
