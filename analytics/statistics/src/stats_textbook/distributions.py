"""How the standard distributions relate, and the exponential family that
explains why so many of them share the same estimation machinery.

The exponential-family objects here are deliberately written as the four
callables in the definition

    log p(x | theta) = eta(theta) * T(x) - A(eta(theta)) + log h(x)

so the notebook can print each piece separately and check the sum against
``scipy``. The point of NB03 is that the pieces are the interesting part.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import special, stats

__all__ = [
    "EXPONENTIAL_FAMILIES",
    "RELATIONS",
    "ExponentialFamily",
    "Relation",
    "binomial_poisson_tv_distance",
    "exponential_family_logpdf",
    "relation_layout",
]


@dataclass(frozen=True)
class Relation:
    """A directed limit or transformation between two distributions."""

    source: str
    target: str
    condition: str


RELATIONS: tuple[Relation, ...] = (
    Relation("bernoulli", "binomial", "n 回の独立和"),
    Relation("binomial", "poisson", "n -> inf, p -> 0, np = lambda 一定"),
    Relation("binomial", "normal", "n -> inf, p 固定 (de Moivre-Laplace)"),
    Relation("poisson", "normal", "lambda -> inf"),
    Relation("exponential", "gamma", "k 個の独立和"),
    Relation("gamma", "chi2", "k = df/2, scale = 2"),
    Relation("normal", "chi2", "標準正規の二乗和"),
    Relation("normal", "t", "正規 / sqrt(chi2/df)"),
    Relation("chi2", "f", "独立な chi2 の比"),
    Relation("t", "normal", "df -> inf"),
)


def relation_layout() -> dict[str, tuple[float, float]]:
    """Fixed positions for the relation graph (NB03's map of the territory)."""
    return {
        "bernoulli": (0.0, 2.0),
        "binomial": (1.0, 2.0),
        "poisson": (2.0, 2.6),
        "normal": (3.0, 1.6),
        "exponential": (0.0, 0.0),
        "gamma": (1.0, 0.0),
        "chi2": (2.2, 0.4),
        "t": (3.6, 0.6),
        "f": (3.2, -0.6),
    }


@dataclass(frozen=True)
class ExponentialFamily:
    """log p(x | theta) = eta(theta) T(x) - A(eta) + log h(x)."""

    name: str
    natural_param: Callable[[float], float]
    sufficient_stat: Callable[[np.ndarray], np.ndarray]
    log_partition: Callable[[float], float]
    log_base_measure: Callable[[np.ndarray], np.ndarray]


def exponential_family_logpdf(family: ExponentialFamily, theta: float, x: np.ndarray) -> np.ndarray:
    """Evaluate the family's log density by assembling its four pieces."""
    x = np.asarray(x, dtype=float)
    eta = family.natural_param(theta)
    return eta * family.sufficient_stat(x) - family.log_partition(eta) + family.log_base_measure(x)


EXPONENTIAL_FAMILIES: dict[str, ExponentialFamily] = {
    # p in (0, 1): eta = logit(p), A(eta) = log(1 + e^eta), h(x) = 1.
    "bernoulli": ExponentialFamily(
        name="bernoulli",
        natural_param=lambda p: math.log(p / (1.0 - p)),
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: float(np.logaddexp(0.0, eta)),
        log_base_measure=lambda x: np.zeros_like(x),
    ),
    # lambda > 0: eta = log(lambda), A(eta) = e^eta, h(x) = 1 / x!.
    "poisson": ExponentialFamily(
        name="poisson",
        natural_param=math.log,
        sufficient_stat=lambda x: x,
        log_partition=math.exp,
        log_base_measure=lambda x: -special.gammaln(x + 1.0),
    ),
    # sigma = 1: eta = mu, A(eta) = eta^2 / 2, h(x) = exp(-x^2/2)/sqrt(2 pi).
    "normal_unit_var": ExponentialFamily(
        name="normal_unit_var",
        natural_param=float,
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: 0.5 * eta**2,
        log_base_measure=lambda x: -0.5 * x**2 - 0.5 * math.log(2.0 * math.pi),
    ),
    # rate > 0: eta = -rate, A(eta) = -log(-eta), h(x) = 1 on x >= 0.
    "exponential": ExponentialFamily(
        name="exponential",
        natural_param=lambda rate: -rate,
        sufficient_stat=lambda x: x,
        log_partition=lambda eta: -math.log(-eta),
        log_base_measure=lambda x: np.zeros_like(x),
    ),
}


def binomial_poisson_tv_distance(n: int, p: float) -> float:
    """Total-variation distance between Binomial(n, p) and Poisson(np).

    Bounded above by ``n * p**2`` (Le Cam), which is why the Poisson limit
    is a good approximation exactly when p is small.
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must lie in [0, 1]; got {p}")
    k = np.arange(0, n + 1)
    binom = stats.binom.pmf(k, n, p)
    pois = stats.poisson.pmf(k, n * p)
    # Poisson has mass above n; the half-sum form accounts for it via the
    # tail that binom assigns zero to.
    tail = 1.0 - stats.poisson.cdf(n, n * p)
    return float(0.5 * (np.abs(binom - pois).sum() + tail))
