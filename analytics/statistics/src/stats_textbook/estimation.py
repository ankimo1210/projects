"""Point estimation: maximum likelihood, Fisher information, Cramer-Rao.

Written for the four exponential families of ``distributions``. Their MLEs
are available in closed form, which lets the notebook compare an analytic
answer against a numerical one and see them agree -- the numerical route is
what generalises, the closed form is what makes it checkable.

The module distinguishes *expected* Fisher information (an average over
hypothetical data at a given theta) from *observed* information (the
curvature of this sample's own log-likelihood). They coincide at the MLE
for these families and part company anywhere else, which is a distinction
NB06 makes concrete rather than glossing over.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .distributions import EXPONENTIAL_FAMILIES, exponential_family_logpdf

__all__ = [
    "MLEResult",
    "cramer_rao_bound",
    "expected_fisher_information",
    "log_likelihood",
    "method_of_moments",
    "mle",
    "observed_information",
]


@dataclass(frozen=True)
class MLEResult:
    """A maximum-likelihood estimate with its asymptotic standard error."""

    estimate: float
    se: float
    loglik: float
    n: int


def _check_family(name: str) -> None:
    if name not in EXPONENTIAL_FAMILIES:
        raise KeyError(f"unknown family {name!r}; expected one of {sorted(EXPONENTIAL_FAMILIES)}")


def log_likelihood(family_name: str, theta: float, x: np.ndarray) -> float:
    """Total log-likelihood of ``x`` under the family at ``theta``."""
    _check_family(family_name)
    return float(
        exponential_family_logpdf(EXPONENTIAL_FAMILIES[family_name], theta, np.asarray(x)).sum()
    )


def method_of_moments(family_name: str, x: np.ndarray) -> float:
    """Match the first moment. For these four families this equals the MLE."""
    _check_family(family_name)
    m = float(np.mean(x))
    if family_name == "exponential":
        return 1.0 / m
    return m


def mle(family_name: str, x: np.ndarray) -> MLEResult:
    """The closed-form maximum-likelihood estimate.

    Every one of these families has the sample mean (or its reciprocal) as
    the MLE, because the sufficient statistic is the sum -- see NB03.
    """
    _check_family(family_name)
    x = np.asarray(x, dtype=float)
    theta_hat = method_of_moments(family_name, x)
    n = x.size
    info = expected_fisher_information(family_name, theta_hat, n)
    return MLEResult(
        estimate=theta_hat,
        se=1.0 / math.sqrt(info),
        loglik=log_likelihood(family_name, theta_hat, x),
        n=n,
    )


def expected_fisher_information(family_name: str, theta: float, n: int = 1) -> float:
    """I(theta) for one observation, times ``n``.

    Closed forms; each is the second derivative of the log-partition
    function pulled back to the original parameter.
    """
    _check_family(family_name)
    if family_name == "bernoulli":
        unit = 1.0 / (theta * (1.0 - theta))
    elif family_name == "poisson":
        unit = 1.0 / theta
    elif family_name == "normal_unit_var":
        unit = 1.0
    else:  # exponential, rate parameterisation
        unit = 1.0 / theta**2
    return n * unit


def observed_information(loglik: Callable[[float], float], theta: float, h: float = 1e-5) -> float:
    """-d^2/dtheta^2 of this sample's log-likelihood, by central difference.

    This is what an estimator actually has access to: the curvature of the
    likelihood it was handed, not an average over data it never saw.
    """
    return -(loglik(theta + h) - 2.0 * loglik(theta) + loglik(theta - h)) / h**2


def cramer_rao_bound(family_name: str, theta: float, n: int) -> float:
    """The smallest variance any unbiased estimator of ``theta`` can have."""
    return 1.0 / expected_fisher_information(family_name, theta, n)
