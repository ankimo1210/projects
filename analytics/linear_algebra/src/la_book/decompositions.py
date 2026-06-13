"""Matrix decomposition helpers: LU / QR / Cholesky / SVD / PCA / whitening."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import linalg as sla


def lu(A):
    """LU with partial pivoting: A = P @ L @ U. Returns (P, L, U)."""
    P, L, U = sla.lu(np.asarray(A, dtype=float))
    return P, L, U


def qr(A):
    """Thin QR: A = Q @ R with orthonormal columns in Q. Returns (Q, R)."""
    return np.linalg.qr(np.asarray(A, dtype=float))


def cholesky(A):
    """Cholesky of a symmetric positive definite A: A = L @ L.T."""
    return np.linalg.cholesky(np.asarray(A, dtype=float))


def svd_lowrank(A, k: int):
    """Best rank-k approximation of A (Eckart-Young) via the SVD."""
    A = np.asarray(A, dtype=float)
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    return (U[:, :k] * s[:k]) @ Vt[:k]


def lowrank_errors(A, ks):
    """Frobenius errors ||A - A_k||_F for each k in ks."""
    A = np.asarray(A, dtype=float)
    return np.array([np.linalg.norm(A - svd_lowrank(A, k), "fro") for k in ks])


def compression_ratio(shape, k: int) -> float:
    """Storage of rank-k factors relative to the full m x n matrix."""
    m, n = shape
    return k * (m + n + 1) / (m * n)


@dataclass
class PCAResult:
    """PCA via SVD of the centered data matrix.

    components has shape (n_components, n_features); rows are the principal
    directions sorted by decreasing explained variance.
    """

    mean: np.ndarray
    components: np.ndarray
    explained_variance: np.ndarray
    explained_variance_ratio: np.ndarray
    scores: np.ndarray


def pca_fit(X, n_components: int | None = None) -> PCAResult:
    """Fit PCA by SVD of the centered data (no covariance matrix formed)."""
    X = np.asarray(X, dtype=float)
    mean = X.mean(axis=0)
    Xc = X - mean
    _U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = s**2 / (X.shape[0] - 1)
    k = len(s) if n_components is None else n_components
    return PCAResult(
        mean=mean,
        components=Vt[:k],
        explained_variance=var[:k],
        explained_variance_ratio=var[:k] / var.sum(),
        scores=Xc @ Vt[:k].T,
    )


def whiten(X, eps: float = 1e-12):
    """PCA whitening: rotate to principal axes, scale each to unit variance.

    Returns (Z, W) with Z = (X - mean) @ W and cov(Z) ~ I.
    """
    X = np.asarray(X, dtype=float)
    mean = X.mean(axis=0)
    Xc = X - mean
    cov = Xc.T @ Xc / (X.shape[0] - 1)
    w, V = np.linalg.eigh(cov)
    # eigh returns ascending eigenvalues; flip to match PCA ordering.
    w, V = w[::-1], V[:, ::-1]
    W = V / np.sqrt(w + eps)
    return Xc @ W, W
