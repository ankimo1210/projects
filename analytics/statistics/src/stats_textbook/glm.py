"""Generalised linear models, fitted by iteratively reweighted least squares.

A GLM is three choices: a distribution from the exponential family (NB03),
a link function tying its mean to a linear predictor, and the data. IRLS
then fits all of them with the same loop -- at each step it forms a working
response and a weight, and runs a weighted least squares. Writing that loop
out is the point of NB10; the agreement with statsmodels is what proves the
loop was written correctly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import special, stats

__all__ = ["GLMResult", "deviance_residuals", "dispersion", "irls"]

_FAMILIES = ("binomial", "poisson", "gaussian")


@dataclass(frozen=True)
class GLMResult:
    """A fitted GLM and the pieces needed to judge it."""

    params: np.ndarray
    se: np.ndarray
    fitted: np.ndarray
    deviance: float
    loglik: float
    n_iter: int
    converged: bool


def _check_family(family: str) -> None:
    if family not in _FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {_FAMILIES}")


def _link_inverse(eta: np.ndarray, family: str) -> np.ndarray:
    """Canonical inverse link: logit, log, or identity."""
    if family == "binomial":
        return special.expit(eta)
    if family == "poisson":
        return np.exp(eta)
    return eta


def _variance(mu: np.ndarray, family: str) -> np.ndarray:
    """The family's mean-variance relationship."""
    if family == "binomial":
        return mu * (1.0 - mu)
    if family == "poisson":
        return mu
    return np.ones_like(mu)


def _deviance(y: np.ndarray, mu: np.ndarray, family: str) -> float:
    """Twice the log-likelihood gap to the saturated model."""
    if family == "binomial":
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(y > 0, y * np.log(y / mu), 0.0)
            b = np.where(y < 1, (1 - y) * np.log((1 - y) / (1 - mu)), 0.0)
        return float(2.0 * np.sum(a + b))
    if family == "poisson":
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / mu), 0.0)
        return float(2.0 * np.sum(term - (y - mu)))
    return float(np.sum((y - mu) ** 2))


def _loglik(y: np.ndarray, mu: np.ndarray, family: str) -> float:
    if family == "binomial":
        return float(np.sum(stats.bernoulli.logpmf(y, mu)))
    if family == "poisson":
        return float(np.sum(stats.poisson.logpmf(y, mu)))
    resid = y - mu
    sigma2 = float(resid @ resid / y.size)
    return float(np.sum(stats.norm.logpdf(y, mu, np.sqrt(sigma2))))


def irls(
    X: np.ndarray,
    y: np.ndarray,
    family: str = "binomial",
    max_iter: int = 50,
    tol: float = 1e-10,
) -> GLMResult:
    """Fit a GLM by iteratively reweighted least squares.

    Each iteration linearises the link around the current fit, forming a
    working response ``z`` and weights ``w``, then solves a weighted least
    squares. For canonical links this is exactly Newton-Raphson on the
    log-likelihood, which is why it converges in a handful of steps.
    """
    _check_family(family)
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if family == "binomial" and np.any((y < 0.0) | (y > 1.0)):
        raise ValueError("binomial response must lie in [0, 1]")

    n, k = X.shape
    # Start from a mildly shrunk response so the link is finite at step 0.
    if family == "binomial":
        mu = (y + 0.5) / 2.0
    elif family == "poisson":
        mu = np.maximum(y, 0.25) + 0.1
    else:
        mu = np.full_like(y, y.mean())
    beta = np.zeros(k)
    converged = False
    # Counted explicitly rather than read off the loop variable afterwards:
    # a for-else or an early break would leave that stale, and n_iter is
    # reported to the caller.
    n_iter = 0

    for _ in range(max_iter):
        n_iter += 1
        var = _variance(mu, family)
        if family == "binomial":
            eta = special.logit(mu)
            dmu_deta = var
        elif family == "poisson":
            eta = np.log(mu)
            dmu_deta = mu
        else:
            eta = mu
            dmu_deta = np.ones_like(mu)
        z = eta + (y - mu) / dmu_deta
        w = dmu_deta**2 / var
        sqrt_w = np.sqrt(w)
        beta_new, *_ = np.linalg.lstsq(X * sqrt_w[:, None], z * sqrt_w, rcond=None)
        mu = _link_inverse(X @ beta_new, family)
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            converged = True
            break
        beta = beta_new

    var = _variance(mu, family)
    if family == "binomial":
        w = var
    elif family == "poisson":
        w = mu
    else:
        w = np.ones_like(mu)
    cov = np.linalg.pinv((X * w[:, None]).T @ X)
    scale = 1.0
    if family == "gaussian":
        resid = y - mu
        scale = float(resid @ resid / (n - k))
    return GLMResult(
        params=beta,
        se=np.sqrt(scale * np.diag(cov)),
        fitted=mu,
        deviance=_deviance(y, mu, family),
        loglik=_loglik(y, mu, family),
        n_iter=n_iter,
        converged=converged,
    )


def deviance_residuals(y: np.ndarray, mu: np.ndarray, family: str) -> np.ndarray:
    """Signed square roots of each observation's deviance contribution."""
    _check_family(family)
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if family == "poisson":
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(y > 0, y * np.log(y / mu), 0.0)
        d = 2.0 * (term - (y - mu))
    elif family == "binomial":
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(y > 0, y * np.log(y / mu), 0.0)
            b = np.where(y < 1, (1 - y) * np.log((1 - y) / (1 - mu)), 0.0)
        d = 2.0 * (a + b)
    else:
        d = (y - mu) ** 2
    return np.sign(y - mu) * np.sqrt(np.maximum(d, 0.0))


def dispersion(result: GLMResult, y: np.ndarray, X: np.ndarray, family: str) -> float:
    """Pearson chi-square over residual degrees of freedom.

    Should sit near 1 when the family's mean-variance relationship holds.
    Well above 1 is overdispersion: the counts vary more than a Poisson
    can, and every standard error from the fit is too small.
    """
    _check_family(family)
    y = np.asarray(y, dtype=float)
    n, k = np.asarray(X).shape
    var = _variance(result.fitted, family)
    chi2 = float(np.sum((y - result.fitted) ** 2 / var))
    return chi2 / (n - k)
