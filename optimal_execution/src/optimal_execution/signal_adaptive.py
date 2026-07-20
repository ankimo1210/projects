"""Signal-adaptive execution (stylized Lehalle–Neuman 2019).

Lehalle & Neuman (2019, *Finance and Stochastics*) derive the optimal
execution program when a Markovian predictive signal — an Ornstein–Uhlenbeck
short-horizon alpha — is traded against transient market impact. This module
implements the lab's stylized discrete form: the expected signal path tilts
the linear-quadratic Almgren–Chriss program, so the schedule leans on the
signal instead of merely averaging risk against impact.

Sell program on the decision grid t_k = k dt, x_{k+1} = X - sum_{j<=k} q_j:

    alpha_bar_k = alpha_0 exp(-kappa_alpha t_k)          (expected drift)
    J(q) = eta sum q_k^2/dt + lambda sigma^2 dt sum x_{k+1}^2
           - dt sum alpha_bar_k x_{k+1}
    min J(q)  s.t.  sum q = X,  q >= 0.

The linear term is exact for a deterministic drift: E[IS] falls by
integral(x_t alpha_t dt) when the price rises while inventory is held. With
alpha_0 = 0 the program IS the discrete Almgren–Chriss problem; with
lambda = 0 as well it is TWAP. q >= 0 keeps a pure liquidation (no
round-trip positions), consistent with the lab's safety layer; the full
singular control of Lehalle–Neuman is intentionally out of scope.
"""

from __future__ import annotations

import numpy as np

from .config import Config


def expected_signal_path(alpha0: float, kappa_alpha: float, T: float, n_steps: int) -> np.ndarray:
    """E[alpha_{t_k} | alpha_0] = alpha_0 exp(-kappa_alpha t_k) on the grid.

    ``alpha0`` is the current signal in currency/share per second (positive =
    price expected to rise); ``kappa_alpha`` its OU mean-reversion rate.
    """
    t = np.arange(n_steps) * (T / n_steps)
    return alpha0 * np.exp(-kappa_alpha * t)


def ln_schedule(
    cfg: Config,
    alpha0: float,
    kappa_alpha: float,
    n_steps: int | None = None,
    lam: float | None = None,
) -> np.ndarray:
    """Signal-tilted LQ-optimal schedule (shares per step, sums to X, >= 0).

    Solves the KKT system of the equality-constrained quadratic program and
    pins negative components to zero with the same active-set loop as
    :func:`optimal_execution.resilience.ow_numeric`.
    """
    n = n_steps or cfg.n_decision_steps
    lam = cfg.risk_aversion_lambda if lam is None else lam
    X = cfg.initial_inventory
    dt = cfg.horizon_seconds / n
    alpha_bar = expected_signal_path(alpha0, kappa_alpha, cfg.horizon_seconds, n)

    L = np.tril(np.ones((n, n)))  # x_{k+1} = X - (L q)_k
    H = 2.0 * cfg.impact.temporary_eta / dt * np.eye(n)
    H += 2.0 * lam * cfg.sigma_abs**2 * dt * (L.T @ L)
    H += 1e-12 * np.trace(H) / n * np.eye(n)  # SPD guard for lam == 0
    ones = np.ones(n)
    b = 2.0 * lam * cfg.sigma_abs**2 * dt * X * (L.T @ ones) - dt * (L.T @ alpha_bar)

    active = np.ones(n, dtype=bool)  # True = free variable
    for _ in range(n):
        idx = np.where(active)[0]
        m = len(idx)
        kkt = np.zeros((m + 1, m + 1))
        kkt[:m, :m] = H[np.ix_(idx, idx)]
        kkt[:m, m] = 1.0
        kkt[m, :m] = 1.0
        rhs = np.concatenate([b[idx], [X]])
        sol = np.linalg.solve(kkt, rhs)
        q_sub = sol[:m]
        if np.all(q_sub >= -1e-9 * X):
            q = np.zeros(n)
            q[idx] = np.maximum(q_sub, 0.0)
            q *= X / q.sum()  # renormalise away the clip epsilon
            return q
        active[idx[q_sub < 0]] = False
    raise RuntimeError("active-set loop failed to converge")
