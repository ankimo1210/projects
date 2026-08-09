"""Numerical linear-algebra helpers used by the B1 chapters.

The functions in this module deliberately expose several least-squares
algorithms.  ``method="inverse"`` is included as a teaching baseline; it
forms an explicit inverse of the normal-equation matrix and should not be
used for serious numerical work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
LeastSquaresMethod = Literal["inverse", "normal", "qr", "svd"]


def _as_matrix(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional array")
    if array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _as_vector(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional array")
    if array.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _validate_weights(weights: ArrayLike | None, n: int) -> FloatArray:
    if weights is None:
        return np.ones(n, dtype=float)
    result = _as_vector(weights, name="weights")
    if result.shape != (n,):
        raise ValueError("weights must have one entry per observation")
    if np.any(result <= 0.0):
        raise ValueError("least-squares weights must be strictly positive")
    return result


@dataclass(frozen=True)
class LeastSquaresDiagnostics:
    """Diagnostics for the (possibly weighted) design matrix.

    ``condition_number`` is the 2-norm condition number of
    :math:`W^{1/2}X`, not of the squared normal-equation matrix.
    """

    residual_norm: float
    weighted_residual_norm: float
    rank: int
    condition_number: float
    n_observations: int
    n_parameters: int


@dataclass(frozen=True)
class LeastSquaresResult:
    """Result returned by :func:`solve_least_squares`."""

    coefficients: FloatArray
    fitted_values: FloatArray
    residuals: FloatArray
    diagnostics: LeastSquaresDiagnostics
    method: LeastSquaresMethod
    ridge: float

    def predict(self, design: ArrayLike) -> FloatArray:
        """Predict responses for a new design matrix."""

        matrix = _as_matrix(design, name="design")
        if matrix.shape[1] != self.coefficients.size:
            raise ValueError("design has a different number of columns")
        return matrix @ self.coefficients


def add_intercept(design: ArrayLike) -> FloatArray:
    """Prepend an intercept column to a design matrix."""

    matrix = _as_matrix(design, name="design")
    return np.column_stack((np.ones(matrix.shape[0]), matrix))


def solve_least_squares(
    design: ArrayLike,
    response: ArrayLike,
    *,
    method: LeastSquaresMethod = "svd",
    weights: ArrayLike | None = None,
    ridge: float = 0.0,
) -> LeastSquaresResult:
    """Solve ordinary, weighted, or ridge-regularized least squares.

    The objective is

    .. math::

       \\sum_i w_i (y_i - x_i^\top\beta)^2 + \alpha\\|\beta\\|_2^2.

    Parameters
    ----------
    design, response:
        Explicit design matrix and one-dimensional response.  An intercept
        is not added implicitly; use :func:`add_intercept` when needed.
    method:
        ``"svd"`` is the robust default.  ``"qr"`` avoids normal equations,
        ``"normal"`` solves them, and ``"inverse"`` explicitly inverts them
        as a deliberately unstable classroom baseline.
    weights:
        Strictly positive precision-style observation weights.
    ridge:
        Non-negative L2 penalty applied to every coefficient.
    """

    matrix = _as_matrix(design, name="design")
    target = _as_vector(response, name="response")
    if target.shape != (matrix.shape[0],):
        raise ValueError("response must have one entry per observation")
    if method not in {"inverse", "normal", "qr", "svd"}:
        raise ValueError(f"unknown least-squares method: {method!r}")
    if not np.isfinite(ridge) or ridge < 0.0:
        raise ValueError("ridge must be a finite non-negative number")

    observation_weights = _validate_weights(weights, matrix.shape[0])
    root_weights = np.sqrt(observation_weights)
    weighted_design = root_weights[:, None] * matrix
    weighted_target = root_weights * target
    n_parameters = matrix.shape[1]

    if method in {"inverse", "normal"}:
        gram = weighted_design.T @ weighted_design
        if ridge:
            gram = gram + ridge * np.eye(n_parameters)
        right_hand_side = weighted_design.T @ weighted_target
        if method == "inverse":
            coefficients = np.linalg.inv(gram) @ right_hand_side
        else:
            coefficients = np.linalg.solve(gram, right_hand_side)
    elif method == "qr":
        qr_design = weighted_design
        qr_target = weighted_target
        if ridge:
            qr_design = np.vstack((qr_design, np.sqrt(ridge) * np.eye(n_parameters)))
            qr_target = np.concatenate((qr_target, np.zeros(n_parameters)))
        if np.linalg.matrix_rank(qr_design) < n_parameters:
            raise np.linalg.LinAlgError(
                "QR solve requires full column rank; use method='svd' for rank-deficient data"
            )
        q_matrix, r_matrix = np.linalg.qr(qr_design, mode="reduced")
        coefficients = np.linalg.solve(r_matrix, q_matrix.T @ qr_target)
    else:
        u_matrix, singular_values, vh_matrix = np.linalg.svd(weighted_design, full_matrices=False)
        projected = u_matrix.T @ weighted_target
        if ridge:
            factors = singular_values / (singular_values**2 + ridge)
        else:
            tolerance = (
                np.finfo(float).eps
                * max(weighted_design.shape)
                * (singular_values[0] if singular_values.size else 0.0)
            )
            factors = np.divide(
                1.0,
                singular_values,
                out=np.zeros_like(singular_values),
                where=singular_values > tolerance,
            )
        coefficients = vh_matrix.T @ (factors * projected)

    fitted_values = matrix @ coefficients
    residuals = target - fitted_values
    diagnostics = LeastSquaresDiagnostics(
        residual_norm=float(np.linalg.norm(residuals)),
        weighted_residual_norm=float(np.linalg.norm(root_weights * residuals)),
        rank=int(np.linalg.matrix_rank(weighted_design)),
        condition_number=float(np.linalg.cond(weighted_design)),
        n_observations=matrix.shape[0],
        n_parameters=n_parameters,
    )
    return LeastSquaresResult(
        coefficients=np.asarray(coefficients, dtype=float),
        fitted_values=np.asarray(fitted_values, dtype=float),
        residuals=np.asarray(residuals, dtype=float),
        diagnostics=diagnostics,
        method=method,
        ridge=float(ridge),
    )


@dataclass(frozen=True)
class PCAResult:
    """Principal components obtained from a centered thin SVD."""

    mean: FloatArray
    components: FloatArray
    scores: FloatArray
    explained_variance: FloatArray
    explained_variance_ratio: FloatArray
    singular_values: FloatArray
    centered: bool

    def transform(self, observations: ArrayLike) -> FloatArray:
        """Project observations onto the fitted components."""

        matrix = _as_matrix(observations, name="observations")
        if matrix.shape[1] != self.mean.size:
            raise ValueError("observations have a different number of features")
        centered = matrix - self.mean if self.centered else matrix
        return centered @ self.components.T

    def inverse_transform(self, scores: ArrayLike | None = None) -> FloatArray:
        """Reconstruct observations from component scores."""

        score_matrix = self.scores if scores is None else _as_matrix(scores, name="scores")
        if score_matrix.shape[1] != self.components.shape[0]:
            raise ValueError("scores have a different number of components")
        reconstructed = score_matrix @ self.components
        return reconstructed + self.mean if self.centered else reconstructed


def _orient_components(components: FloatArray, scores: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Choose a deterministic orientation using the largest loading."""

    largest_indices = np.argmax(np.abs(components), axis=1)
    signs = np.sign(components[np.arange(components.shape[0]), largest_indices])
    signs[signs == 0.0] = 1.0
    return components * signs[:, None], scores * signs[None, :]


def pca_from_svd(
    observations: ArrayLike,
    n_components: int | None = None,
    *,
    center: bool = True,
) -> PCAResult:
    """Fit PCA using a numerically stable thin SVD.

    The component rows are oriented so that their largest-magnitude loading
    is positive.  This convention improves reproducibility but does not
    remove the mathematical sign indeterminacy of eigenvectors.
    """

    matrix = _as_matrix(observations, name="observations")
    if matrix.shape[0] < 2:
        raise ValueError("PCA requires at least two observations")
    maximum_components = min(matrix.shape)
    if n_components is None:
        n_components = maximum_components
    if isinstance(n_components, bool) or not isinstance(n_components, (int, np.integer)):
        raise TypeError("n_components must be an integer or None")
    if not 1 <= int(n_components) <= maximum_components:
        raise ValueError(f"n_components must be between 1 and {maximum_components}")

    mean = matrix.mean(axis=0) if center else np.zeros(matrix.shape[1])
    centered_matrix = matrix - mean if center else matrix
    _, all_singular_values, all_vh = np.linalg.svd(centered_matrix, full_matrices=False)
    components = all_vh[:n_components].copy()
    singular_values = all_singular_values[:n_components].copy()
    scores = centered_matrix @ components.T
    components, scores = _orient_components(components, scores)

    all_variances = all_singular_values**2 / (matrix.shape[0] - 1)
    explained_variance = singular_values**2 / (matrix.shape[0] - 1)
    total_variance = float(all_variances.sum())
    if total_variance == 0.0:
        explained_variance_ratio = np.zeros_like(explained_variance)
    else:
        explained_variance_ratio = explained_variance / total_variance

    return PCAResult(
        mean=np.asarray(mean, dtype=float),
        components=np.asarray(components, dtype=float),
        scores=np.asarray(scores, dtype=float),
        explained_variance=np.asarray(explained_variance, dtype=float),
        explained_variance_ratio=np.asarray(explained_variance_ratio, dtype=float),
        singular_values=np.asarray(singular_values, dtype=float),
        centered=center,
    )


def align_component_signs(
    components: ArrayLike,
    reference: ArrayLike,
    *,
    scores: ArrayLike | None = None,
) -> tuple[FloatArray, FloatArray | None]:
    """Flip component signs to align corresponding rows with a reference.

    Components are assumed to be in the same order.  If scores are supplied,
    their columns receive the same sign flips so reconstruction is unchanged.
    """

    candidates = _as_matrix(components, name="components")
    reference_matrix = _as_matrix(reference, name="reference")
    if candidates.shape != reference_matrix.shape:
        raise ValueError("components and reference must have the same shape")
    signs = np.sign(np.einsum("ij,ij->i", candidates, reference_matrix))
    signs[signs == 0.0] = 1.0
    aligned_components = candidates * signs[:, None]

    if scores is None:
        return aligned_components, None
    score_matrix = _as_matrix(scores, name="scores")
    if score_matrix.shape[1] != candidates.shape[0]:
        raise ValueError("scores must have one column per component")
    return aligned_components, score_matrix * signs[None, :]
