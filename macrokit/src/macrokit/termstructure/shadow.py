"""Wu and Xia (2016) three-factor shadow-rate term structure model (design §4.3).

Units: annual percent, one period = one month. Shadow rate s_t = delta0 + 1'X_t,
short rate max(r_L, s_t). Under Q, X' = rho_Q X + Sigma e with rho_Q diagonal and
mu_Q = 0 (Wu-Xia normalization); under P, X' = mu + rho X + Sigma e. One-month
forward from month n to n+1: f_n = r_L + sd_n g((a_n + b_n'X - r_L) / sd_n),
g(z) = z Phi(z) + phi(z), with
  b_n = rho_Q^n,  a_n = delta0 - (1/2400) s_n' Omega s_n,  s_n = (1 - rho_Q^n)/(1 - rho_Q),
  sd_n^2 = sum_{j<n} (rho_Q^j)' Omega rho_Q^j,  Omega = Sigma Sigma'.

The likelihood is evaluated for a batch of parameter vectors at once, so one
call returns a value and its finite-difference gradient. The state covariance
is symmetrized after every predict and update step; the 2026-10-17 prototype
broke down numerically after ~70 periods without it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr

from .curve import ZeroPanel
from .var import expected_average

FORWARD_MONTHS = np.array([3, 6, 12, 24, 60, 84, 120])
N_PARAMS = 23
CONVEXITY = 1.0 / 1200.0
PENALTY = 1e12
_SQRT_2PI = np.sqrt(2.0 * np.pi)
_LOG_2PI = np.log(2.0 * np.pi)
_TRIL = ((0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2))
_DIAG = frozenset({0, 2, 5})


@dataclass(frozen=True)
class ShadowParams:
    """Every field carries a leading batch axis B."""

    rho_q: np.ndarray  # (B, 3), 1 > rho_q1 > rho_q2 > rho_q3 > 0
    delta0: np.ndarray  # (B,)
    sigma: np.ndarray  # (B, 3, 3) lower triangular
    mu: np.ndarray  # (B, 3)
    rho: np.ndarray  # (B, 3, 3)
    omega: np.ndarray  # (B,) measurement error sd, annual %


def _logistic(u: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-u))


def _logit(p: float) -> float:
    return float(np.log(p) - np.log1p(-p))


def pack(rho_q, delta0, sigma, mu, rho, omega) -> np.ndarray:
    """Unconstrained 23-vector: ordered rho_Q, delta0, chol(Sigma) (log diag), mu, rho, log omega."""
    r1, r2, r3 = (float(v) for v in rho_q)
    sigma = np.asarray(sigma, dtype=float)
    tri = [np.log(sigma[r, c]) if j in _DIAG else sigma[r, c] for j, (r, c) in enumerate(_TRIL)]
    return np.concatenate(
        [
            [_logit(r1), _logit(r2 / r1), _logit(r3 / r2), float(delta0)],
            tri,
            np.asarray(mu, dtype=float),
            np.asarray(rho, dtype=float).ravel(),
            [np.log(float(omega))],
        ]
    )


def unpack(theta: np.ndarray) -> ShadowParams:
    theta = np.atleast_2d(theta)
    size = theta.shape[0]
    r1 = _logistic(theta[:, 0])
    r2 = r1 * _logistic(theta[:, 1])
    r3 = r2 * _logistic(theta[:, 2])
    sigma = np.zeros((size, 3, 3))
    for j, (r, c) in enumerate(_TRIL):
        value = theta[:, 4 + j]
        sigma[:, r, c] = np.exp(value) if j in _DIAG else value
    return ShadowParams(
        rho_q=np.column_stack([r1, r2, r3]),
        delta0=theta[:, 3].copy(),
        sigma=sigma,
        mu=theta[:, 10:13].copy(),
        rho=theta[:, 13:22].reshape(size, 3, 3).copy(),
        omega=np.exp(theta[:, 22]),
    )


def forward_loadings(p: ShadowParams, months: np.ndarray):
    """a (B, M), b (B, M, 3), sd (B, M) of the shadow one-month forwards."""
    rq = p.rho_q[:, None, :]
    n = np.asarray(months, dtype=float)[None, :, None]
    b = rq**n
    s = (1.0 - rq**n) / (1.0 - rq)
    omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
    a = p.delta0[:, None] - 0.5 * CONVEXITY * np.einsum("bmk,bkl,bml->bm", s, omega, s)
    prod = p.rho_q[:, :, None] * p.rho_q[:, None, :]
    geo = (1.0 - prod[:, None] ** n[..., None]) / (1.0 - prod[:, None])
    sd = np.sqrt(np.einsum("bkl,bmkl->bm", omega, geo))
    return a, b, sd


def _g(z: np.ndarray) -> np.ndarray:
    return z * ndtr(z) + np.exp(-0.5 * z * z) / _SQRT_2PI


def shadow_forwards(
    theta: np.ndarray, states: np.ndarray, r_lower: float, months: np.ndarray
) -> np.ndarray:
    """Model one-month forwards (annual %) for one parameter vector: (T, M)."""
    a, b, sd = forward_loadings(unpack(theta), months)
    z = (a[0] + states @ b[0].T - r_lower) / sd[0]
    return r_lower + sd[0] * _g(z)


def loglik(
    theta: np.ndarray,
    forwards: np.ndarray,
    r_lower: float,
    months: np.ndarray = FORWARD_MONTHS,
    return_states: bool = False,
):
    """Extended-Kalman-filter log-likelihood for each row of ``theta`` (B, 23) or (23,).

    Members with non-stationary P dynamics, a non-positive innovation covariance, or
    non-finite values get ``-PENALTY`` instead of raising.
    """
    theta = np.atleast_2d(theta)
    size, n_obs = theta.shape[0], len(months)
    with np.errstate(all="ignore"):
        p = unpack(theta)
        a, b, sd = forward_loadings(p, months)
        omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
        finite = np.isfinite(theta).all(axis=1)
        raw_rho = np.where(finite[:, None, None], p.rho, 0.0)  # eigvals raises on NaN
        ok = finite & (np.abs(np.linalg.eigvals(raw_rho)).max(axis=1) < 1.0)
        rho = np.where(ok[:, None, None], p.rho, 0.0)
        rho_t = np.swapaxes(rho, 1, 2)
        kron = np.einsum("bij,bkl->bikjl", rho, rho).reshape(size, 9, 9)
        cov = np.linalg.solve(np.eye(9) - kron, omega.reshape(size, 9, 1)).reshape(size, 3, 3)
        cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
        x = np.linalg.solve(np.eye(3) - rho, p.mu[..., None])[..., 0]
        meas = (p.omega**2)[:, None, None] * np.eye(n_obs)
        total = np.zeros(size)
        states = np.empty((size, len(forwards), 3)) if return_states else None
        try:
            for t in range(len(forwards)):
                if t > 0:
                    x = p.mu + np.einsum("bij,bj->bi", rho, x)
                    cov = rho @ cov @ rho_t + omega
                    cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
                z = (a + np.einsum("bmk,bk->bm", b, x) - r_lower) / sd
                resid = forwards[t] - (r_lower + sd * _g(z))
                jac_cov = (ndtr(z)[..., None] * b) @ cov  # H P, (B, M, 3)
                innov = jac_cov @ np.swapaxes(ndtr(z)[..., None] * b, 1, 2) + meas
                sign, logdet = np.linalg.slogdet(innov)
                solved = np.linalg.solve(innov, np.concatenate([resid[..., None], jac_cov], axis=2))
                x = x + np.einsum("bmk,bm->bk", jac_cov, solved[..., 0])
                cov = cov - np.swapaxes(jac_cov, 1, 2) @ solved[..., 1:]
                cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
                total += -0.5 * (
                    logdet + np.einsum("bm,bm->b", resid, solved[..., 0]) + n_obs * _LOG_2PI
                )
                ok &= sign > 0
                if states is not None:
                    states[:, t] = x
        except np.linalg.LinAlgError:
            ok[:] = False
        total = np.where(ok & np.isfinite(total), total, -PENALTY)
    return (total, states) if return_states else total


def filtered_states(theta: np.ndarray, forwards: np.ndarray, r_lower: float) -> np.ndarray:
    _, states = loglik(theta, forwards, r_lower, return_states=True)
    return states[0]


def shadow_rate(theta: np.ndarray, states: np.ndarray) -> np.ndarray:
    return unpack(theta).delta0[0] + states.sum(axis=1)


def expected_short_average(
    theta: np.ndarray, states: np.ndarray, r_lower: float, horizon: int
) -> np.ndarray:
    """Mean over h = 0..horizon-1 of E_t[max(r_L, s_{t+h})] under P (closed form).

    ``theta`` (23,) with ``states`` (T, 3) returns (T,); ``theta`` (B, 23) with
    ``states`` (B, T, 3) returns (B, T).
    """
    single = np.ndim(theta) == 1
    theta = np.atleast_2d(theta)
    states = states[None] if states.ndim == 2 else states
    p = unpack(theta)
    omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
    rho_t = np.swapaxes(p.rho, 1, 2)
    mean_x = states.copy()
    var_x = np.zeros((len(theta), 3, 3))
    total = np.zeros(states.shape[:2])
    for _ in range(horizon):
        m = p.delta0[:, None] + mean_x.sum(axis=2)
        sd = np.sqrt(np.maximum(var_x.sum(axis=(1, 2)), 0.0))[:, None]
        with np.errstate(divide="ignore", invalid="ignore"):
            d = (m - r_lower) / sd
            smooth = r_lower + (m - r_lower) * ndtr(d) + sd * np.exp(-0.5 * d * d) / _SQRT_2PI
        total += np.where(sd > 0, smooth, np.maximum(r_lower, m))
        mean_x = p.mu[:, None, :] + mean_x @ rho_t
        var_x = p.rho @ var_x @ rho_t + omega
    out = total / horizon
    return out[0] if single else out


def expected_gaussian_average(theta: np.ndarray, states: np.ndarray, horizon: int) -> np.ndarray:
    """The same average without the bound (for gate G3 ①)."""
    p = unpack(theta)
    return expected_average(p.mu[0], p.rho[0], p.delta0[0], np.ones(3), states, horizon)


def panel_forwards(panel: ZeroPanel, months: np.ndarray = FORWARD_MONTHS) -> np.ndarray:
    """One-month forwards (annual %) from zero yields: (n+1) y_{n+1} - n y_n."""
    n = np.asarray(months)
    return (n + 1) * panel.columns(n + 1) - n * panel.columns(n)
