"""Known data-generating processes for gate G1 and the small-sample study (design §5).

Parameters are fixed constants here; none is calibrated to Japanese data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .acm import AcmFit, pricing_recursion
from .curve import ZeroPanel, month_ends
from .dns import ns_loadings
from .shadow import FORWARD_MONTHS, expected_short_average, pack, shadow_forwards, unpack
from .var import expected_average


@dataclass(frozen=True)
class AffineParams:
    """Gaussian affine model: x' = mu + phi x + chol e, r = delta0 + delta1'x (decimal per month)."""

    mu: np.ndarray
    phi: np.ndarray
    chol: np.ndarray
    lambda0: np.ndarray
    lambda1: np.ndarray
    delta0: float
    delta1: np.ndarray
    sigma2: float = 0.0

    @classmethod
    def from_fit(cls, fit: AcmFit) -> AffineParams:
        return cls(
            fit.var.mu,
            fit.var.phi,
            np.linalg.cholesky(fit.var.sigma),
            fit.lambda0,
            fit.lambda1,
            fit.delta0,
            fit.delta1,
            fit.sigma2,
        )


@dataclass(frozen=True)
class SyntheticCurve:
    panel: ZeroPanel
    expected_pct: np.ndarray  # true design-§2.1 E_t for the 120-month horizon
    short_pct: np.ndarray  # true one-month rate (annual %), the bracket-2 expectation


def simulate_affine(
    params: AffineParams,
    n_months: int,
    rng: np.random.Generator,
    *,
    max_months: int = 120,
    noise_pct: float = 0.02,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticCurve:
    k = len(params.mu)
    x = np.linalg.solve(np.eye(k) - params.phi, params.mu)
    shocks = rng.standard_normal((burn_in + n_months, k)) @ params.chol.T
    path = np.empty((n_months, k))
    for t in range(burn_in + n_months):
        x = params.mu + params.phi @ x + shocks[t]
        if t >= burn_in:
            path[t - burn_in] = x
    a, b = pricing_recursion(
        params.mu - params.lambda0,
        params.phi - params.lambda1,
        params.chol @ params.chol.T,
        params.sigma2,
        params.delta0,
        params.delta1,
        max_months,
    )
    months = np.arange(1, max_months + 1)
    yields = -1200.0 / months * (a[1:] + path @ b[1:].T)
    yields = yields + noise_pct * rng.standard_normal(yields.shape)
    expected = 1200.0 * expected_average(
        params.mu, params.phi, params.delta0, params.delta1, path, horizon
    )
    short = 1200.0 * (params.delta0 + path @ params.delta1)
    return SyntheticCurve(ZeroPanel(month_ends(n_months), months, yields), expected, short)


_PHI = np.diag([0.99, 0.95, 0.90])
_PHI_Q = np.diag([0.995, 0.93, 0.85])
AFFINE_TRUE = AffineParams(
    mu=np.zeros(3),
    phi=_PHI,
    chol=np.diag([0.25, 0.15, 0.10]) / 1200.0,
    # lambda0 shifts the Q mean of factor 1 by +0.5 pp (annual)
    lambda0=-np.array([0.5 * (1 - _PHI_Q[0, 0]), 0.0, 0.0]) / 1200.0,
    lambda1=_PHI - _PHI_Q,
    delta0=2.0 / 1200.0,
    delta1=np.ones(3),
)


def affine_dgp(n_months: int, rng: np.random.Generator) -> SyntheticCurve:
    return simulate_affine(AFFINE_TRUE, n_months, rng)


DNS_MEAN = np.array([4.0, -2.0, 0.0])
DNS_PHI = np.diag([0.99, 0.95, 0.90])
DNS_SHOCK = np.array([0.25, 0.30, 0.50])


def dns_dgp(
    n_months: int,
    rng: np.random.Generator,
    *,
    max_months: int = 120,
    noise_pct: float = 0.02,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticCurve:
    mu = (np.eye(3) - DNS_PHI) @ DNS_MEAN
    f = DNS_MEAN.copy()
    path = np.empty((n_months, 3))
    shocks = rng.standard_normal((burn_in + n_months, 3)) * DNS_SHOCK
    for t in range(burn_in + n_months):
        f = mu + DNS_PHI @ f + shocks[t]
        if t >= burn_in:
            path[t - burn_in] = f
    months = np.arange(1, max_months + 1)
    yields = path @ ns_loadings(months).T + noise_pct * rng.standard_normal((n_months, max_months))
    short_loading = ns_loadings(np.array([1.0]))[0]
    expected = expected_average(mu, DNS_PHI, 0.0, short_loading, path, horizon)
    return SyntheticCurve(
        ZeroPanel(month_ends(n_months), months, yields), expected, path @ short_loading
    )


SHADOW_TRUE = pack(
    rho_q=(0.997, 0.95, 0.8),
    delta0=1.0,
    sigma=np.array([[0.15, 0.0, 0.0], [0.05, 0.2, 0.0], [0.0, -0.05, 0.25]]),
    mu=np.zeros(3),
    rho=np.diag([0.99, 0.94, 0.8]),
    omega=0.05,
)


@dataclass(frozen=True)
class SyntheticShadow:
    dates: tuple[date, ...]
    forwards: np.ndarray  # (T, 7) observed one-month forwards at FORWARD_MONTHS
    yield_pct: np.ndarray  # observed 10-year zero yield
    expected_pct: np.ndarray  # true E_t, 120 months
    short_pct: np.ndarray  # true short rate max(r_L, s)
    states: np.ndarray


def shadow_dgp(
    n_months: int,
    rng: np.random.Generator,
    *,
    r_lower: float = 0.0,
    theta: np.ndarray = SHADOW_TRUE,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticShadow:
    p = unpack(theta)
    mu, rho, chol, omega = p.mu[0], p.rho[0], p.sigma[0], p.omega[0]
    x = np.linalg.solve(np.eye(3) - rho, mu)
    shocks = rng.standard_normal((burn_in + n_months, 3)) @ chol.T
    states = np.empty((n_months, 3))
    for t in range(burn_in + n_months):
        x = mu + rho @ x + shocks[t]
        if t >= burn_in:
            states[t - burn_in] = x
    forwards = shadow_forwards(theta, states, r_lower, np.arange(1, horizon + 1))  # n = 1..horizon
    short = np.maximum(r_lower, p.delta0[0] + states.sum(axis=1))
    zero = (short + forwards[:, : horizon - 1].sum(axis=1)) / horizon  # mean of n = 0..horizon-1
    observed = forwards[:, FORWARD_MONTHS - 1] + omega * rng.standard_normal((n_months, 7))
    return SyntheticShadow(
        month_ends(n_months),
        observed,
        zero + omega * rng.standard_normal(n_months),
        expected_short_average(theta, states, r_lower, horizon),
        short,
        states,
    )
