"""Statistical risk factors from the return covariance (PCA) and risk concentration.

A principal-component decomposition of the asset return covariance recovers the
dominant common factors: the first eigenvector is the direction of greatest
co-movement (typically "the market"), its eigenvalue share is how much of total
variance it explains. When a few factors explain most of the variance, the book is
really making only a few independent bets — quantified by :func:`effective_n_bets`,
the inverse Herfindahl of the explained-variance shares (n if all eigenvalues are
equal, →1 if one factor dominates).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PCAFactors:
    """Eigen-decomposition of a return covariance, largest factor first."""

    explained_variance_ratio: pd.Series  # share of total variance per factor
    loadings: pd.DataFrame  # assets × factors (eigenvectors)


def _cov_eig(rets: pd.DataFrame):
    cov = rets.dropna(how="any").cov().to_numpy(dtype=float)
    vals, vecs = np.linalg.eigh(cov)  # ascending, symmetric
    order = np.argsort(vals)[::-1]  # largest first
    return vals[order], vecs[:, order]


def pca_factors(rets: pd.DataFrame, n_components: int = 5) -> PCAFactors:
    """Top ``n_components`` statistical risk factors of the return covariance."""
    vals, vecs = _cov_eig(rets)
    total = vals.sum()
    k = min(n_components, len(vals))
    names = [f"PC{i + 1}" for i in range(k)]
    evr = pd.Series(
        vals[:k] / total if total else vals[:k], index=names, name="explained_variance_ratio"
    )
    loadings = pd.DataFrame(vecs[:, :k], index=rets.columns, columns=names)
    return PCAFactors(explained_variance_ratio=evr, loadings=loadings)


def effective_n_bets(rets: pd.DataFrame) -> float:
    """Effective number of independent risk factors = ``1 / Σ share_i²`` over eigenvalues.

    Equals the asset count when all eigenvalues are equal (fully diversified) and
    approaches 1 when a single factor explains nearly all the variance.
    """
    vals, _ = _cov_eig(rets)
    total = vals.sum()
    if total <= 0:
        return float("nan")
    shares = vals / total
    return float(1.0 / np.sum(shares**2))
