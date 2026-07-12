"""Fractional Gaussian noise and fractional Brownian-motion simulators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import cholesky, toeplitz

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class EmbeddingDiagnostics:
    """Numerical diagnostics for a circulant covariance embedding."""

    method: str
    min_eigenvalue: float
    max_eigenvalue: float
    negative_eigenvalues: int
    clipped_mass: float
    fallback_used: bool = False


@dataclass(frozen=True)
class FbmResult:
    """Simulation time grid, fBM paths and embedding diagnostics."""

    times: FloatArray
    paths: FloatArray
    diagnostics: EmbeddingDiagnostics


def _validate_h(h: float) -> None:
    if not np.isfinite(h) or not 0 < h < 1:
        raise ValueError("Hurst exponent must lie strictly between 0 and 1")


def _validate_sizes(n: int, n_paths: int) -> None:
    if not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("n must be a positive integer")
    if not isinstance(n_paths, (int, np.integer)) or n_paths < 1:
        raise ValueError("n_paths must be a positive integer")


def fgn_autocovariance(h: float, n_lags: int) -> FloatArray:
    r"""Return unit-spacing fGn autocovariances for lags ``0..n_lags``.

    The formula is

    .. math::

       \gamma(k)=\tfrac12\left(|k+1|^{2H}-2|k|^{2H}+|k-1|^{2H}\right).
    """
    _validate_h(h)
    if not isinstance(n_lags, (int, np.integer)) or n_lags < 0:
        raise ValueError("n_lags must be a non-negative integer")
    k = np.arange(n_lags + 1, dtype=np.float64)
    return 0.5 * (
        np.abs(k + 1.0) ** (2.0 * h) - 2.0 * np.abs(k) ** (2.0 * h) + np.abs(k - 1.0) ** (2.0 * h)
    )


def davies_harte_fgn(
    h: float,
    n: int,
    n_paths: int,
    rng: np.random.Generator,
    *,
    tol_rel: float = 1e-10,
) -> tuple[FloatArray, EmbeddingDiagnostics]:
    """Simulate unit-spacing fGn with the Davies--Harte embedding.

    Tiny negative FFT eigenvalues attributable to floating-point round-off are
    clipped and quantified.  A materially indefinite embedding raises instead
    of silently altering the covariance.
    """
    _validate_h(h)
    _validate_sizes(n, n_paths)
    if tol_rel < 0:
        raise ValueError("tol_rel must be non-negative")

    gamma = fgn_autocovariance(h, n)
    circulant_row = np.concatenate((gamma[:n], gamma[n : n + 1], gamma[1:n][::-1]))
    eigenvalues = np.fft.fft(circulant_row).real
    min_eigenvalue = float(eigenvalues.min())
    max_eigenvalue = float(eigenvalues.max())
    threshold = tol_rel * max(max_eigenvalue, np.finfo(np.float64).tiny)
    if min_eigenvalue < -threshold:
        raise np.linalg.LinAlgError(
            "Davies-Harte circulant embedding is materially indefinite: "
            f"min={min_eigenvalue:.3e}, tolerance={threshold:.3e}"
        )

    negative = eigenvalues < 0
    clipped_mass = float(-eigenvalues[negative].sum())
    negative_count = int(negative.sum())
    eigenvalues = np.maximum(eigenvalues, 0.0)

    # One complex FFT produces two independent real fGn paths.  NumPy's FFT is
    # unnormalised, hence the 2n denominator inside the square root.
    n_complex = (n_paths + 1) // 2
    xi = rng.standard_normal((n_complex, 2 * n))
    eta = rng.standard_normal((n_complex, 2 * n))
    scale = np.sqrt(eigenvalues / (2.0 * n))
    transformed = np.fft.fft((xi + 1j * eta) * scale, axis=1)
    paths = np.concatenate((transformed.real[:, :n], transformed.imag[:, :n]), axis=0)[:n_paths]

    diagnostics = EmbeddingDiagnostics(
        method="davies-harte",
        min_eigenvalue=min_eigenvalue,
        max_eigenvalue=max_eigenvalue,
        negative_eigenvalues=negative_count,
        clipped_mass=clipped_mass,
    )
    return np.asarray(paths, dtype=np.float64), diagnostics


def cholesky_fgn(
    h: float,
    n: int,
    n_paths: int,
    rng: np.random.Generator,
) -> FloatArray:
    """Simulate exact finite-dimensional fGn via a Toeplitz Cholesky factor."""
    _validate_h(h)
    _validate_sizes(n, n_paths)
    gamma = fgn_autocovariance(h, n - 1)
    covariance = toeplitz(gamma)
    factor = cholesky(covariance, lower=True, check_finite=False)
    normals = rng.standard_normal((n_paths, n))
    return np.asarray(normals @ factor.T, dtype=np.float64)


def fbm_paths(
    h: float,
    n: int,
    n_paths: int,
    horizon: float,
    rng: np.random.Generator,
    *,
    method: str = "davies-harte",
) -> FbmResult:
    """Simulate fBM paths on an equally spaced grid including ``B_0=0``."""
    _validate_h(h)
    _validate_sizes(n, n_paths)
    if not np.isfinite(horizon) or horizon <= 0:
        raise ValueError("horizon must be positive")

    if method == "davies-harte":
        try:
            increments, diagnostics = davies_harte_fgn(h, n, n_paths, rng)
        except np.linalg.LinAlgError:
            if n > 2048:
                raise
            increments = cholesky_fgn(h, n, n_paths, rng)
            diagnostics = EmbeddingDiagnostics(
                method="cholesky",
                min_eigenvalue=float("nan"),
                max_eigenvalue=float("nan"),
                negative_eigenvalues=0,
                clipped_mass=0.0,
                fallback_used=True,
            )
    elif method == "cholesky":
        increments = cholesky_fgn(h, n, n_paths, rng)
        diagnostics = EmbeddingDiagnostics(
            method="cholesky",
            min_eigenvalue=float("nan"),
            max_eigenvalue=float("nan"),
            negative_eigenvalues=0,
            clipped_mass=0.0,
        )
    else:
        raise ValueError("method must be 'davies-harte' or 'cholesky'")

    increments *= (horizon / n) ** h
    paths = np.empty((n_paths, n + 1), dtype=np.float64)
    paths[:, 0] = 0.0
    np.cumsum(increments, axis=1, out=paths[:, 1:])
    times = np.linspace(0.0, horizon, n + 1, dtype=np.float64)
    return FbmResult(times=times, paths=paths, diagnostics=diagnostics)
