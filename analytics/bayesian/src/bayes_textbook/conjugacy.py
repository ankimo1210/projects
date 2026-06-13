"""Conjugate prior families with closed-form updates and predictives.

Each class is a tiny immutable record: ``update`` returns a NEW posterior
object, so the prior -> posterior flow reads like the math:

    prior = BetaBinomial(2, 2)
    post  = prior.update(successes=34, failures=16)

These closed forms are the ground truth the MCMC chapters are checked against.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class BetaBinomial:
    """theta ~ Beta(alpha, beta), x | theta ~ Binomial."""

    alpha: float
    beta: float

    def update(self, successes: int, failures: int) -> BetaBinomial:
        return BetaBinomial(self.alpha + successes, self.beta + failures)

    @property
    def dist(self):
        return stats.beta(self.alpha, self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def map(self) -> float:
        """Posterior mode; defined for alpha, beta > 1."""
        if self.alpha <= 1 or self.beta <= 1:
            raise ValueError("MAP requires alpha > 1 and beta > 1")
        return (self.alpha - 1) / (self.alpha + self.beta - 2)

    def credible_interval(self, level: float = 0.95):
        tail = (1 - level) / 2
        return self.dist.ppf(tail), self.dist.ppf(1 - tail)

    def sample(self, n: int, seed: int = 42):
        return self.dist.rvs(n, random_state=np.random.default_rng(seed))

    def posterior_predictive(self, n_new: int):
        """Distribution of future successes in n_new trials (Beta-Binomial).

        Returns (k values, pmf).
        """
        k = np.arange(n_new + 1)
        return k, stats.betabinom(n_new, self.alpha, self.beta).pmf(k)


@dataclass(frozen=True)
class GammaPoisson:
    """lam ~ Gamma(shape=alpha, rate=beta), x | lam ~ Poisson."""

    alpha: float
    beta: float

    def update(self, total_count: int, n_obs: int) -> GammaPoisson:
        return GammaPoisson(self.alpha + total_count, self.beta + n_obs)

    @property
    def dist(self):
        return stats.gamma(self.alpha, scale=1.0 / self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / self.beta

    def credible_interval(self, level: float = 0.95):
        tail = (1 - level) / 2
        return self.dist.ppf(tail), self.dist.ppf(1 - tail)

    def posterior_predictive(self, k_max: int = 30):
        """Distribution of one future count (Negative Binomial). Returns (k, pmf)."""
        k = np.arange(k_max + 1)
        p = self.beta / (self.beta + 1.0)
        return k, stats.nbinom(self.alpha, p).pmf(k)


@dataclass(frozen=True)
class NormalNormal:
    """mu ~ Normal(mu0, tau0^2) with KNOWN observation sd sigma."""

    mu0: float
    tau0: float
    sigma: float

    def update(self, data) -> NormalNormal:
        data = np.asarray(data, dtype=float)
        n = len(data)
        prec = 1.0 / self.tau0**2 + n / self.sigma**2
        tau_n = np.sqrt(1.0 / prec)
        mu_n = tau_n**2 * (self.mu0 / self.tau0**2 + data.sum() / self.sigma**2)
        return NormalNormal(mu_n, tau_n, self.sigma)

    @property
    def dist(self):
        return stats.norm(self.mu0, self.tau0)

    @property
    def mean(self) -> float:
        return self.mu0

    def credible_interval(self, level: float = 0.95):
        tail = (1 - level) / 2
        return self.dist.ppf(tail), self.dist.ppf(1 - tail)

    def posterior_predictive(self):
        """One future observation: Normal(mu_n, sigma^2 + tau_n^2)."""
        return stats.norm(self.mu0, np.sqrt(self.sigma**2 + self.tau0**2))


@dataclass(frozen=True)
class DirichletMultinomial:
    """p ~ Dirichlet(alpha vector), counts | p ~ Multinomial."""

    alpha: tuple

    def update(self, counts) -> DirichletMultinomial:
        counts = np.asarray(counts, dtype=float)
        return DirichletMultinomial(tuple(np.asarray(self.alpha) + counts))

    @property
    def mean(self):
        a = np.asarray(self.alpha, dtype=float)
        return a / a.sum()

    def sample(self, n: int, seed: int = 42):
        return np.random.default_rng(seed).dirichlet(np.asarray(self.alpha), size=n)
