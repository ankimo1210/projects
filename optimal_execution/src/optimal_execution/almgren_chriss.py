"""Almgren–Chriss optimal execution (continuous solution + discretisation).

Objective (sell program, linear temporary impact, mean–variance):

    J[x] = int_0^T [ eta * xdot^2 + lambda * sigma^2 * x^2 ] dt,
    kappa = sqrt(lambda * sigma^2 / eta),
    x*(t) = X sinh(kappa (T - t)) / sinh(kappa T)  ->  X (1 - t/T) as kappa -> 0.

Discrete quantities on the decision grid t_k = k dt:

    q_k   = x_k - x_{k+1}                      (child order, shares)
    E[C]  = gamma/2 X^2 + eta sum q_k^2 / dt   (+ half-spread * X, fees)
    V[C]  = sum sigma_k^2 dt x_{k+1}^2         (timing risk; x_{k+1} is the
            inventory exposed to the step-k price move, consistent with
            trades executing at step-start prices in the simulator)

All costs are in currency; helpers convert to bps of arrival notional.
"""

from __future__ import annotations

import numpy as np

from .config import Config
from .price_process import sigma_profile

_KAPPA_T_TINY = 1e-6


def ac_inventory(X: float, T: float, kappa: float, n_steps: int) -> np.ndarray:
    """Optimal inventory x_k on the grid k = 0..n_steps (x_0 = X, x_N = 0).

    Numerically stable for large kappa*T via the exponential form
    sinh(a)/sinh(b) = exp(a - b) (1 - exp(-2a)) / (1 - exp(-2b)).
    """
    t = np.linspace(0.0, T, n_steps + 1)
    kT = kappa * T
    if kT < _KAPPA_T_TINY:
        # risk-neutral limit: TWAP with O((kT)^2) correction terms ignored
        return X * (1.0 - t / T)
    a = kappa * (T - t)
    ratio = np.exp(a - kT) * (1.0 - np.exp(-2.0 * a)) / (1.0 - np.exp(-2.0 * kT))
    return X * ratio


def ac_schedule(X: float, T: float, kappa: float, n_steps: int) -> np.ndarray:
    """Child orders q_k = x_k - x_{k+1} (shares, all >= 0), length n_steps."""
    x = ac_inventory(X, T, kappa, n_steps)
    return -np.diff(x)


def ac_expected_cost(cfg: Config, q: np.ndarray, include_spread_fees: bool = True) -> float:
    """Expected implementation shortfall (currency) of a deterministic schedule."""
    dt = cfg.horizon_seconds / len(q)
    X = float(np.sum(q))
    cost = cfg.impact.permanent_gamma / 2.0 * X * X
    cost += cfg.impact.temporary_eta * float(np.sum(q * q)) / dt
    if include_spread_fees:
        cost += (cfg.half_spread + cfg.fee_per_share) * X
    return cost


def ac_cost_variance(cfg: Config, q: np.ndarray) -> float:
    """Timing-risk variance (currency^2) of a deterministic schedule."""
    n = len(q)
    dt = cfg.horizon_seconds / n
    x = np.concatenate([[np.sum(q)], np.sum(q) - np.cumsum(q)])  # x_0..x_N
    sig = sigma_profile(cfg, n)
    return float(np.sum(sig**2 * dt * x[1:] ** 2))


def ac_continuous_cost(cfg: Config, kappa: float, n_fine: int = 4000) -> float:
    """Fine-grid approximation of the continuous-time impact cost integral
    gamma/2 X^2 + int eta xdot^2 dt (no spread/fees), for consistency tests."""
    X, T = cfg.initial_inventory, cfg.horizon_seconds
    q = ac_schedule(X, T, kappa, n_fine)
    dt = T / n_fine
    return (
        cfg.impact.permanent_gamma / 2.0 * X * X
        + cfg.impact.temporary_eta * float(np.sum(q * q)) / dt
    )


def kappa_for_lambda(cfg: Config, lam: float) -> float:
    """kappa = sqrt(lambda sigma^2 / eta) using the average sigma."""
    return float(np.sqrt(lam * cfg.sigma_abs**2 / cfg.impact.temporary_eta))


def efficient_frontier(cfg: Config, lambdas: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Expected-cost vs timing-risk frontier over a risk-aversion grid.

    Returns arrays keyed: lambda, kappa_T, expected_cost, cost_sd (currency)
    plus *_bps versions (bps of arrival notional).
    """
    if lambdas is None:
        lambdas = np.logspace(-9, -4, 41)
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    e_cost = np.empty(len(lambdas))
    sd = np.empty(len(lambdas))
    kTs = np.empty(len(lambdas))
    for i, lam in enumerate(lambdas):
        kappa = kappa_for_lambda(cfg, lam)
        q = ac_schedule(X, T, kappa, N)
        e_cost[i] = ac_expected_cost(cfg, q)
        sd[i] = np.sqrt(ac_cost_variance(cfg, q))
        kTs[i] = kappa * T
    to_bps = 1e4 / cfg.notional
    return {
        "lambda": np.asarray(lambdas, dtype=float),
        "kappa_T": kTs,
        "expected_cost": e_cost,
        "cost_sd": sd,
        "expected_cost_bps": e_cost * to_bps,
        "cost_sd_bps": sd * to_bps,
    }
