"""Gaussian copula and portfolio credit loss (A4 deep-dive).

The single-factor Gaussian copula is the model behind CDO pricing — and the 2008
story that *correlation*, not marginal default risk, drives tail losses. Provides
the finite-pool loss simulator, the Vasicek large-pool loss CDF (closed form), the
conditional default probability, and correlated copula samples for the scatter.

References: Li (2000), "On default correlation: a copula function approach";
Vasicek (2002); Hull Ch.24-25.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def portfolio_loss_samples(pd, rho, n_names=100, n_sims=20_000, rng=None):
    """Loss fraction of a homogeneous pool under the one-factor Gaussian copula.

    asset_i = sqrt(rho)·M + sqrt(1-rho)·eps_i; name i defaults if asset_i < Φ⁻¹(pd).
    The marginal default probability is ``pd`` for any ``rho``; correlation only
    reshapes the *distribution* of the pool loss. Returns ``n_sims`` loss fractions.
    """
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must be in [0, 1)")
    if rng is None:
        rng = np.random.default_rng(0)
    threshold = norm.ppf(pd)
    m = rng.standard_normal((n_sims, 1))
    eps = rng.standard_normal((n_sims, n_names))
    asset = np.sqrt(rho) * m + np.sqrt(1.0 - rho) * eps
    return (asset < threshold).mean(axis=1)


def vasicek_loss_cdf(loss, pd, rho):
    """Vasicek large-homogeneous-pool loss CDF P(L ≤ loss) (closed form)."""
    x = np.clip(loss, 1e-12, 1.0 - 1e-12)
    return norm.cdf((np.sqrt(1.0 - rho) * norm.ppf(x) - norm.ppf(pd)) / np.sqrt(rho))


def conditional_default_prob(pd, rho, factor):
    """P(default | systemic factor M=factor) (Vasicek; Hull eq. 24.8).

    A bad (low) factor lifts every name's default probability together — the
    mechanism of correlated tail losses.
    """
    return norm.cdf((norm.ppf(pd) - np.sqrt(rho) * factor) / np.sqrt(1.0 - rho))


def gaussian_copula_samples(rho, n=4000, rng=None):
    """Correlated uniforms (u, v) from a bivariate Gaussian copula with correlation rho.

    Used for the scatter that shows tail clustering as rho grows.
    """
    if rng is None:
        rng = np.random.default_rng(0)
    z = rng.standard_normal((n, 2))
    x = z[:, 0]
    y = rho * z[:, 0] + np.sqrt(1.0 - rho**2) * z[:, 1]
    return norm.cdf(x), norm.cdf(y)
