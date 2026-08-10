"""OLS covariance estimators matched to common dependence structures.

The point estimate is always OLS.  Changing the covariance estimator does not
repair omitted variables, measurement error, nonlinearity, or other coefficient
bias.  HAC observations must already be in time order, and cluster labels must
identify the sampling dependence unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
CovarianceType = Literal["naive", "HC0", "HC1", "HC2", "HC3", "HAC", "cluster"]


def _design(X: ArrayLike) -> FloatArray:
    design = np.asarray(X, dtype=float)
    if design.ndim != 2 or design.shape[0] < 2 or design.shape[1] < 1:
        raise ValueError("X must be a two-dimensional array with at least two rows")
    if not np.all(np.isfinite(design)):
        raise ValueError("X must contain only finite values")
    return design


def _residuals(values: ArrayLike, n_observations: int) -> FloatArray:
    residuals = np.asarray(values, dtype=float)
    if residuals.shape != (n_observations,):
        raise ValueError("residuals must have one entry per row of X")
    if not np.all(np.isfinite(residuals)):
        raise ValueError("residuals must contain only finite values")
    return residuals


def _scaled_design(design: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Scale each nonzero column for unit-invariant rank and QR calculations."""

    column_scales = np.max(np.abs(design), axis=0)
    if np.any(column_scales == 0.0):
        raise np.linalg.LinAlgError("the design contains an all-zero column")
    scaled = design / column_scales
    if not np.all(np.isfinite(scaled)):
        raise FloatingPointError("design scaling produced non-finite values")
    return scaled, column_scales


def _covariance_type(value: str) -> CovarianceType:
    if not isinstance(value, str):
        raise TypeError("covariance_type must be a string")
    aliases: dict[str, CovarianceType] = {
        "naive": "naive",
        "hc0": "HC0",
        "hc1": "HC1",
        "hc2": "HC2",
        "hc3": "HC3",
        "hac": "HAC",
        "cluster": "cluster",
    }
    normalized = aliases.get(value.casefold())
    if normalized is None:
        raise ValueError(f"unknown covariance_type: {value!r}")
    return normalized


def _small_sample_flag(value: bool) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError("small_sample must be a boolean")
    return bool(value)


def _cluster_codes(clusters: ArrayLike, n_observations: int) -> tuple[NDArray[np.int64], int]:
    labels = np.asarray(clusters)
    if labels.ndim != 1 or labels.size != n_observations:
        raise ValueError("clusters must have one label per row of X")
    mapping: dict[object, int] = {}
    codes = np.empty(n_observations, dtype=np.int64)
    for index, raw_label in enumerate(labels.tolist()):
        label = raw_label.item() if isinstance(raw_label, np.generic) else raw_label
        missing = pd.isna(label)
        scalar_missing = bool(missing) if np.ndim(missing) == 0 else False
        if scalar_missing or (isinstance(label, (float, complex)) and not np.isfinite(label)):
            raise ValueError("clusters must not contain missing or non-finite labels")
        try:
            code = mapping.setdefault(label, len(mapping))
        except TypeError as error:
            raise TypeError("cluster labels must be hashable") from error
        codes[index] = code
    if len(mapping) < 2:
        raise ValueError("cluster covariance requires at least two clusters")
    return codes, len(mapping)


def _hac_lag(max_lag: int | None, n_observations: int) -> int:
    if max_lag is None:
        return min(n_observations - 1, int(np.floor(4.0 * (n_observations / 100.0) ** (2.0 / 9.0))))
    if isinstance(max_lag, bool) or not isinstance(max_lag, (int, np.integer)):
        raise TypeError("max_lag must be an integer or None")
    if not 0 <= max_lag < n_observations:
        raise ValueError("max_lag must be between zero and n_observations - 1")
    return int(max_lag)


@dataclass(frozen=True)
class OLSCovarianceDiagnostics:
    """Inputs and finite-sample choices behind an OLS covariance estimate."""

    covariance_type: CovarianceType
    n_observations: int
    n_coefficients: int
    residual_degrees_of_freedom: int
    max_lag: int | None
    n_clusters: int | None
    small_sample_correction: bool
    correction_factor: float
    maximum_leverage: float
    minimum_one_minus_leverage: float
    dependence_assumption: str
    warnings: tuple[str, ...]


def _covariance_calculation(
    design: FloatArray,
    residuals: FloatArray,
    *,
    covariance_type: CovarianceType,
    max_lag: int | None,
    clusters: ArrayLike | None,
    small_sample: bool,
) -> tuple[FloatArray, OLSCovarianceDiagnostics]:
    n_observations, n_coefficients = design.shape
    residual_df = n_observations - n_coefficients
    if residual_df <= 0:
        raise ValueError("covariance estimation requires positive residual degrees of freedom")
    numerical_design, column_scales = _scaled_design(design)
    if np.linalg.matrix_rank(numerical_design) < n_coefficients:
        raise np.linalg.LinAlgError("covariance estimation requires a full-column-rank design")
    orthonormal_design, triangular_factor = np.linalg.qr(
        numerical_design,
        mode="reduced",
    )
    inverse_triangular = np.linalg.solve(
        triangular_factor,
        np.eye(n_coefficients, dtype=float),
    )
    leverage = np.sum(orthonormal_design**2, axis=1)
    one_minus_leverage = 1.0 - leverage
    leverage_tolerance = 100.0 * np.finfo(float).eps
    warnings: list[str] = []
    effective_lag: int | None = None
    n_clusters: int | None = None
    correction = 1.0

    if covariance_type == "naive":
        if max_lag is not None or clusters is not None:
            raise ValueError("max_lag and clusters are not used by naive covariance")
        sigma_squared = float(residuals @ residuals / residual_df)
        scaled_covariance = sigma_squared * (inverse_triangular @ inverse_triangular.T)
        dependence_assumption = "homoskedastic, conditionally uncorrelated errors"
    elif covariance_type in {"HC0", "HC1", "HC2", "HC3"}:
        if max_lag is not None or clusters is not None:
            raise ValueError("max_lag and clusters are not used by HC covariance")
        if covariance_type in {"HC2", "HC3"} and np.any(one_minus_leverage <= leverage_tolerance):
            raise np.linalg.LinAlgError(
                f"{covariance_type} is undefined when leverage is numerically one"
            )
        squared_residuals = residuals**2
        if covariance_type == "HC1":
            correction = n_observations / residual_df
            squared_residuals = correction * squared_residuals
        elif covariance_type == "HC2":
            squared_residuals = squared_residuals / one_minus_leverage
        elif covariance_type == "HC3":
            squared_residuals = squared_residuals / one_minus_leverage**2
        orthonormal_meat = orthonormal_design.T @ (squared_residuals[:, None] * orthonormal_design)
        scaled_covariance = inverse_triangular @ orthonormal_meat @ inverse_triangular.T
        dependence_assumption = "heteroskedastic but conditionally uncorrelated errors"
    elif covariance_type == "HAC":
        if clusters is not None:
            raise ValueError("clusters are not used by HAC covariance")
        effective_lag = _hac_lag(max_lag, n_observations)
        scores = orthonormal_design * residuals[:, None]
        orthonormal_meat = scores.T @ scores
        for lag in range(1, effective_lag + 1):
            weight = 1.0 - lag / (effective_lag + 1.0)
            lagged_cross_product = scores[lag:].T @ scores[:-lag]
            orthonormal_meat += weight * (lagged_cross_product + lagged_cross_product.T)
        if small_sample:
            correction = n_observations / residual_df
            orthonormal_meat *= correction
        scaled_covariance = inverse_triangular @ orthonormal_meat @ inverse_triangular.T
        dependence_assumption = "ordered weakly dependent errors within the HAC bandwidth"
    else:
        if max_lag is not None:
            raise ValueError("max_lag is not used by cluster covariance")
        if clusters is None:
            raise ValueError("clusters are required for cluster covariance")
        codes, n_clusters = _cluster_codes(clusters, n_observations)
        scores = orthonormal_design * residuals[:, None]
        cluster_scores = np.zeros((n_clusters, n_coefficients), dtype=float)
        np.add.at(cluster_scores, codes, scores)
        orthonormal_meat = cluster_scores.T @ cluster_scores
        if small_sample:
            correction = (n_clusters / (n_clusters - 1.0)) * ((n_observations - 1.0) / residual_df)
            orthonormal_meat *= correction
        scaled_covariance = inverse_triangular @ orthonormal_meat @ inverse_triangular.T
        dependence_assumption = "arbitrary dependence within, independence across clusters"
        if n_clusters < 30:
            warnings.append(
                "fewer than 30 clusters; asymptotic cluster inference may be unreliable"
            )

    if float(np.max(leverage)) > 0.5:
        warnings.append("maximum leverage exceeds 0.5; HC estimates may be unstable")
    scaled_condition_number = float(np.linalg.cond(numerical_design))
    if scaled_condition_number > 1e7:
        warnings.append(
            "scaled design condition number exceeds 1e7; coefficient covariance "
            "may lose digits in the requested units"
        )
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        inverse_scales = 1.0 / column_scales
        covariance = scaled_covariance * np.outer(inverse_scales, inverse_scales)
    covariance = 0.5 * (covariance + covariance.T)
    if not np.all(np.isfinite(covariance)):
        raise FloatingPointError("covariance calculation produced non-finite values")
    diagonal = np.diag(covariance)
    negative_tolerance = -100.0 * np.finfo(float).eps * max(1.0, float(np.max(np.abs(diagonal))))
    if np.any(diagonal < negative_tolerance):
        raise FloatingPointError("covariance has a materially negative diagonal entry")
    diagnostics = OLSCovarianceDiagnostics(
        covariance_type=covariance_type,
        n_observations=n_observations,
        n_coefficients=n_coefficients,
        residual_degrees_of_freedom=residual_df,
        max_lag=effective_lag,
        n_clusters=n_clusters,
        small_sample_correction=covariance_type == "HC1"
        or (small_sample and covariance_type in {"HAC", "cluster"}),
        correction_factor=float(correction),
        maximum_leverage=float(np.max(leverage)),
        minimum_one_minus_leverage=float(np.min(one_minus_leverage)),
        dependence_assumption=dependence_assumption,
        warnings=tuple(warnings),
    )
    return covariance, diagnostics


def ols_covariance(
    X: ArrayLike,
    residuals: ArrayLike,
    *,
    covariance_type: str = "HC3",
    max_lag: int | None = None,
    clusters: ArrayLike | None = None,
    small_sample: bool = True,
) -> FloatArray:
    """Estimate an OLS coefficient covariance for a specified dependence model."""

    design = _design(X)
    residual_array = _residuals(residuals, design.shape[0])
    covariance, _ = _covariance_calculation(
        design,
        residual_array,
        covariance_type=_covariance_type(covariance_type),
        max_lag=max_lag,
        clusters=clusters,
        small_sample=_small_sample_flag(small_sample),
    )
    return covariance


@dataclass(frozen=True)
class OLSInferenceDiagnostics:
    """Point-estimator and covariance diagnostics for one OLS fit."""

    design_rank: int
    design_condition_number: float
    scaled_design_condition_number: float
    residual_autocorrelation_lag1: float
    covariance: OLSCovarianceDiagnostics
    remaining_bias_warning: str = (
        "robust covariance changes uncertainty, not omitted-variable or measurement-error bias"
    )


@dataclass(frozen=True)
class OLSInferenceResult:
    """OLS coefficients with a separately selected covariance estimator."""

    coefficients: FloatArray
    covariance: FloatArray
    standard_errors: FloatArray
    fitted_values: FloatArray
    residuals: FloatArray
    n_observations: int
    diagnostics: OLSInferenceDiagnostics


def fit_ols_inference(
    X: ArrayLike,
    y: ArrayLike,
    *,
    covariance_type: str = "HC3",
    max_lag: int | None = None,
    clusters: ArrayLike | None = None,
    small_sample: bool = True,
) -> OLSInferenceResult:
    """Fit OLS and attach naive, HC, HAC, or one-way cluster covariance."""

    design = _design(X)
    response = np.asarray(y, dtype=float)
    if response.shape != (design.shape[0],):
        raise ValueError("y must have one entry per row of X")
    if not np.all(np.isfinite(response)):
        raise ValueError("y must contain only finite values")
    numerical_design, column_scales = _scaled_design(design)
    rank = int(np.linalg.matrix_rank(numerical_design))
    if rank < design.shape[1]:
        raise np.linalg.LinAlgError("OLS inference requires a full-column-rank design")
    if design.shape[0] <= design.shape[1]:
        raise ValueError("OLS inference requires positive residual degrees of freedom")
    scaled_coefficients, *_ = np.linalg.lstsq(
        numerical_design,
        response,
        rcond=None,
    )
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        coefficients = scaled_coefficients / column_scales
    if not np.all(np.isfinite(coefficients)):
        raise FloatingPointError("coefficients cannot be represented in the input units")
    fitted = numerical_design @ scaled_coefficients
    residual_array = response - fitted
    covariance, covariance_diagnostics = _covariance_calculation(
        design,
        residual_array,
        covariance_type=_covariance_type(covariance_type),
        max_lag=max_lag,
        clusters=clusters,
        small_sample=_small_sample_flag(small_sample),
    )
    if residual_array.size > 1:
        centered_first = residual_array[:-1] - residual_array[:-1].mean()
        centered_second = residual_array[1:] - residual_array[1:].mean()
        denominator = np.linalg.norm(centered_first) * np.linalg.norm(centered_second)
        autocorrelation = (
            float(centered_first @ centered_second / denominator)
            if denominator > 0.0
            else float("nan")
        )
    else:
        autocorrelation = float("nan")
    return OLSInferenceResult(
        coefficients=np.asarray(coefficients, dtype=float),
        covariance=covariance,
        standard_errors=np.sqrt(np.maximum(np.diag(covariance), 0.0)),
        fitted_values=fitted,
        residuals=residual_array,
        n_observations=design.shape[0],
        diagnostics=OLSInferenceDiagnostics(
            design_rank=rank,
            design_condition_number=float(np.linalg.cond(design)),
            scaled_design_condition_number=float(np.linalg.cond(numerical_design)),
            residual_autocorrelation_lag1=autocorrelation,
            covariance=covariance_diagnostics,
        ),
    )
