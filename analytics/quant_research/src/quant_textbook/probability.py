"""Multivariate-Gaussian helpers for the B2 probability chapters.

All random sampling requires an explicit :class:`numpy.random.Generator`.
Covariance matrices are treated as positive semidefinite objects: tiny
negative eigenvalues caused by roundoff are clipped only after being
compared with a scale-aware tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.random import Generator
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
FactorizationMethod = Literal["auto", "cholesky", "eigh"]


def _as_vector(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _as_covariance(values: ArrayLike, *, dimension: int | None = None) -> FloatArray:
    covariance = np.asarray(values, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] == 0:
        raise ValueError("covariance must be a non-empty two-dimensional array")
    if covariance.shape[0] != covariance.shape[1]:
        raise ValueError("covariance must be square")
    if dimension is not None and covariance.shape != (dimension, dimension):
        raise ValueError("covariance shape must match the mean dimension")
    if not np.all(np.isfinite(covariance)):
        raise ValueError("covariance must contain only finite values")
    symmetry_error = float(np.linalg.norm(covariance - covariance.T, ord=np.inf))
    symmetry_scale = max(
        float(np.linalg.norm(covariance, ord=np.inf)),
        np.finfo(float).tiny,
    )
    symmetry_tolerance = 100.0 * np.finfo(float).eps * covariance.shape[0] * symmetry_scale
    if symmetry_error > symmetry_tolerance:
        raise ValueError("covariance must be symmetric")
    return (covariance + covariance.T) / 2.0


def _require_generator(rng: Generator) -> Generator:
    if not isinstance(rng, Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    return rng


def _eigenvalue_tolerance(eigenvalues: FloatArray, dimension: int) -> float:
    scale = float(np.max(np.abs(eigenvalues)))
    if scale == 0.0:
        scale = 1.0
    return float(np.finfo(float).eps * max(dimension, 1) * scale * 100.0)


@dataclass(frozen=True)
class CovarianceDiagnostics:
    """Numerical diagnostics for a symmetric positive-semidefinite matrix."""

    dimension: int
    numerical_rank: int
    minimum_eigenvalue: float
    maximum_eigenvalue: float
    condition_number: float
    tolerance: float
    is_positive_definite: bool


def validate_covariance(covariance: ArrayLike) -> CovarianceDiagnostics:
    """Validate a covariance matrix and report scale-aware PSD diagnostics.

    A matrix with an eigenvalue below ``-tolerance`` is rejected.  Singular
    and near-singular PSD matrices are valid, with infinite condition number
    when no eigenvalue is numerically positive.
    """

    matrix = _as_covariance(covariance)
    eigenvalues = np.linalg.eigvalsh(matrix)
    tolerance = _eigenvalue_tolerance(eigenvalues, matrix.shape[0])
    if eigenvalues[0] < -tolerance:
        raise ValueError("covariance must be positive semidefinite")
    positive = eigenvalues > tolerance
    numerical_rank = int(np.count_nonzero(positive))
    if numerical_rank == 0 or numerical_rank < matrix.shape[0]:
        condition_number = float("inf")
    else:
        condition_number = float(eigenvalues[-1] / eigenvalues[0])
    return CovarianceDiagnostics(
        dimension=matrix.shape[0],
        numerical_rank=numerical_rank,
        minimum_eigenvalue=float(eigenvalues[0]),
        maximum_eigenvalue=float(eigenvalues[-1]),
        condition_number=condition_number,
        tolerance=tolerance,
        is_positive_definite=bool(eigenvalues[0] > tolerance),
    )


@dataclass(frozen=True)
class CovarianceFactor:
    """A factor ``L`` such that ``L @ L.T`` reconstructs the covariance."""

    factor: FloatArray
    method: Literal["cholesky", "eigh"]
    diagnostics: CovarianceDiagnostics


def covariance_factor(
    covariance: ArrayLike,
    *,
    method: FactorizationMethod = "auto",
) -> CovarianceFactor:
    """Factor a PSD covariance with Cholesky or clipped eigendecomposition."""

    matrix = _as_covariance(covariance)
    diagnostics = validate_covariance(matrix)
    if method not in {"auto", "cholesky", "eigh"}:
        raise ValueError(f"unknown covariance factorization method: {method!r}")

    selected: Literal["cholesky", "eigh"]
    if method == "auto":
        selected = "cholesky" if diagnostics.is_positive_definite else "eigh"
    else:
        selected = method

    if selected == "cholesky":
        if not diagnostics.is_positive_definite:
            raise np.linalg.LinAlgError(
                "Cholesky factorization requires a numerically positive-definite covariance"
            )
        factor = np.linalg.cholesky(matrix)
    else:
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        clipped = np.clip(eigenvalues, 0.0, None)
        factor = eigenvectors * np.sqrt(clipped)[None, :]
    return CovarianceFactor(np.asarray(factor, dtype=float), selected, diagnostics)


def correlated_gaussian(
    mean: ArrayLike,
    covariance: ArrayLike,
    n_samples: int,
    *,
    rng: Generator,
    method: FactorizationMethod = "auto",
) -> FloatArray:
    """Draw correlated Gaussian rows with shape ``(n_samples, dimension)``."""

    location = _as_vector(mean, name="mean")
    matrix = _as_covariance(covariance, dimension=location.size)
    if isinstance(n_samples, bool) or not isinstance(n_samples, (int, np.integer)):
        raise TypeError("n_samples must be an integer")
    if n_samples < 1:
        raise ValueError("n_samples must be at least one")
    generator = _require_generator(rng)
    decomposition = covariance_factor(matrix, method=method)
    standard = generator.standard_normal((int(n_samples), location.size))
    return np.asarray(location + standard @ decomposition.factor.T, dtype=float)


@dataclass(frozen=True)
class ConditionalGaussian:
    """Conditional law of unobserved coordinates given observed coordinates."""

    mean: FloatArray
    covariance: FloatArray
    gain: FloatArray
    target_indices: tuple[int, ...]
    observed_indices: tuple[int, ...]
    observed_rank: int
    observed_condition_number: float


def _index_tuple(indices: ArrayLike, *, dimension: int) -> tuple[int, ...]:
    raw = np.asarray(indices)
    if raw.ndim != 1 or raw.size == 0:
        raise ValueError("observed_indices must be a non-empty one-dimensional array")
    if raw.dtype.kind not in {"i", "u"}:
        raise TypeError("observed_indices must contain integers")
    result = tuple(int(index) for index in raw)
    if len(set(result)) != len(result):
        raise ValueError("observed_indices must not contain duplicates")
    if any(index < 0 or index >= dimension for index in result):
        raise ValueError("observed_indices are out of bounds")
    if len(result) == dimension:
        raise ValueError("at least one coordinate must remain unobserved")
    return result


def conditional_gaussian(
    mean: ArrayLike,
    covariance: ArrayLike,
    observed_indices: ArrayLike,
    observed_values: ArrayLike,
) -> ConditionalGaussian:
    """Return the analytic conditional multivariate-Gaussian distribution.

    A Moore--Penrose inverse is used for a singular observed block.  In that
    case, observed values must lie in the block's affine support; otherwise
    the conditioning event is inconsistent with the specified Gaussian law.
    """

    location = _as_vector(mean, name="mean")
    matrix = _as_covariance(covariance, dimension=location.size)
    diagnostics = validate_covariance(matrix)
    observed = _index_tuple(observed_indices, dimension=location.size)
    values = _as_vector(observed_values, name="observed_values")
    if values.shape != (len(observed),):
        raise ValueError("observed_values must have one entry per observed index")
    target = tuple(index for index in range(location.size) if index not in observed)

    observed_block = matrix[np.ix_(observed, observed)]
    block_diagnostics = validate_covariance(observed_block)
    block_eigenvalues, block_eigenvectors = np.linalg.eigh(observed_block)
    support_positive = block_eigenvalues > 0.0
    support_rank = int(np.count_nonzero(support_positive))
    inverse: FloatArray | None = None
    if support_rank == len(observed):
        try:
            inverse = np.linalg.solve(observed_block, np.eye(len(observed)))
        except np.linalg.LinAlgError:
            pass
    if inverse is None:
        support_positive = block_eigenvalues > block_diagnostics.tolerance
        support_rank = int(np.count_nonzero(support_positive))
        positive_vectors = block_eigenvectors[:, support_positive]
        inverse = (
            positive_vectors / block_eigenvalues[support_positive][None, :]
        ) @ positive_vectors.T
    delta = values - location[list(observed)]
    if support_rank < len(observed):
        null_vectors = block_eigenvectors[:, ~support_positive]
        support_residual = null_vectors.T @ delta
        support_scale = max(
            float(np.linalg.norm(delta)),
            float(np.sqrt(max(block_diagnostics.maximum_eigenvalue, 0.0))),
            np.finfo(float).tiny,
        )
        support_tolerance = 1_000.0 * np.finfo(float).eps * max(len(observed), 1) * support_scale
        if np.linalg.norm(support_residual) > support_tolerance:
            raise ValueError("observed_values are inconsistent with the singular Gaussian support")

    cross = matrix[np.ix_(target, observed)]
    gain = cross @ inverse
    conditional_mean = location[list(target)] + gain @ delta
    conditional_covariance = matrix[np.ix_(target, target)] - gain @ cross.T
    conditional_covariance = (conditional_covariance + conditional_covariance.T) / 2.0
    conditional_eigenvalues, conditional_eigenvectors = np.linalg.eigh(conditional_covariance)
    conditional_tolerance = _eigenvalue_tolerance(
        conditional_eigenvalues, conditional_covariance.shape[0]
    )
    if conditional_eigenvalues[0] < -10.0 * max(conditional_tolerance, diagnostics.tolerance):
        raise FloatingPointError("conditional covariance lost positive semidefiniteness")
    conditional_covariance = (
        conditional_eigenvectors * np.clip(conditional_eigenvalues, 0.0, None)[None, :]
    ) @ conditional_eigenvectors.T

    return ConditionalGaussian(
        mean=np.asarray(conditional_mean, dtype=float),
        covariance=np.asarray(conditional_covariance, dtype=float),
        gain=np.asarray(gain, dtype=float),
        target_indices=target,
        observed_indices=observed,
        observed_rank=block_diagnostics.numerical_rank,
        observed_condition_number=block_diagnostics.condition_number,
    )
