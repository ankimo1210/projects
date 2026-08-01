"""Linear regression read as inference rather than as curve fitting.

The coefficients are estimates, so they have a sampling distribution, and
every t and F below is a statement about that distribution under a set of
assumptions. Those assumptions are the interesting part -- ``robust_se``
exists because one of them (constant error variance) fails routinely, and
the fix costs nothing.

Deliberately built on numpy alone. ``statsmodels`` appears only in the
tests, as the reference implementation this must agree with.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

__all__ = ["OLSResult", "f_test_overall", "leverage", "ols", "robust_se", "vif"]

_HC_KINDS = ("HC0", "HC1", "HC2", "HC3")


@dataclass(frozen=True)
class OLSResult:
    """A least-squares fit with everything needed to do inference on it."""

    params: np.ndarray
    se: np.ndarray
    tvalues: np.ndarray
    pvalues: np.ndarray
    fitted: np.ndarray
    resid: np.ndarray
    df_resid: int
    r_squared: float
    sigma2: float


def ols(X: np.ndarray, y: np.ndarray) -> OLSResult:
    """Ordinary least squares by the normal equations, via ``lstsq``.

    ``lstsq`` rather than an explicit inverse: it is the numerically stable
    route and degrades gracefully on near-collinear designs, which the VIF
    section deliberately constructs.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    params, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ params
    resid = y - fitted
    df_resid = n - k
    sigma2 = float(resid @ resid / df_resid)
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(sigma2 * np.diag(xtx_inv))
    tvalues = params / se
    pvalues = 2.0 * stats.t.sf(np.abs(tvalues), df_resid)
    tss = float(((y - y.mean()) ** 2).sum())
    return OLSResult(
        params=params,
        se=se,
        tvalues=tvalues,
        pvalues=pvalues,
        fitted=fitted,
        resid=resid,
        df_resid=df_resid,
        r_squared=1.0 - float(resid @ resid) / tss,
        sigma2=sigma2,
    )


def leverage(X: np.ndarray) -> np.ndarray:
    """Diagonal of the hat matrix: how much each point pulls its own fit."""
    X = np.asarray(X, dtype=float)
    return np.einsum("ij,jk,ik->i", X, np.linalg.pinv(X.T @ X), X)


def robust_se(X: np.ndarray, resid: np.ndarray, kind: str = "HC0") -> np.ndarray:
    """Heteroskedasticity-consistent standard errors (White's sandwich).

    The ordinary formula assumes every observation has the same error
    variance. When it does not, the coefficients stay unbiased but their
    standard errors are wrong -- and the t statistics built from them
    inherit the error. HC3 is the usual default in small samples.
    """
    if kind not in _HC_KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {_HC_KINDS}")
    X = np.asarray(X, dtype=float)
    resid = np.asarray(resid, dtype=float)
    n, k = X.shape
    h = leverage(X)
    if kind == "HC0":
        w = resid**2
    elif kind == "HC1":
        w = resid**2 * n / (n - k)
    elif kind == "HC2":
        w = resid**2 / (1.0 - h)
    else:
        w = resid**2 / (1.0 - h) ** 2
    bread = np.linalg.pinv(X.T @ X)
    meat = X.T @ (X * w[:, None])
    return np.sqrt(np.diag(bread @ meat @ bread))


def f_test_overall(result: OLSResult, X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Test that every slope is zero, against the intercept-only model."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    k = X.shape[1]
    df_model = k - 1
    tss = float(((y - y.mean()) ** 2).sum())
    rss = float(result.resid @ result.resid)
    f = ((tss - rss) / df_model) / (rss / result.df_resid)
    return f, float(stats.f.sf(f, df_model, result.df_resid))


def vif(X: np.ndarray) -> np.ndarray:
    """Variance inflation factor per column; ``nan`` for a constant column.

    VIF_j = 1 / (1 - R2_j), where R2_j regresses column j on the others.
    A value of 10 means that coefficient's variance is 10 times what it
    would be with uncorrelated predictors.
    """
    X = np.asarray(X, dtype=float)
    k = X.shape[1]
    out = np.full(k, np.nan)
    for j in range(k):
        if np.allclose(X[:, j], X[0, j]):
            continue  # constant column: no variance to inflate
        others = np.delete(X, j, axis=1)
        r2 = ols(others, X[:, j]).r_squared
        out[j] = 1.0 / (1.0 - r2) if r2 < 1.0 else np.inf
    return out
