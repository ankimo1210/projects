"""Obizhaeva–Wang-style execution with resilient (transient) liquidity.

Model: purely transient linear impact with displacement state

    dD_t = -rho D_t dt + eta_t v_t dt  (continuous)      /
    D_{k+1} = exp(-rho dt) (D_k + eta_t q_k)  (discrete, point-impulse),

executed against a block-shaped book so the expected cost of a schedule is

    C(q) = eta_t * [ 1/2 sum_k q_k^2 + sum_{j<k} q_k q_j G((k-j) dt) ]
         = 1/2 eta_t q' M q,   M_kj = G(|k-j| dt), M_kk = 1,

where M is the kernel correlation matrix — symmetric positive definite for
exponential (and completely monotone power-law) kernels, so the scheduling
QP is well posed.

Two solvers are provided:

* :func:`ow_closed_form` — the classical risk-neutral Obizhaeva–Wang (2013)
  solution for exponential resilience: block trades of size X / (rho T + 2)
  at t=0 and t=T plus a constant rate rho X / (rho T + 2) in between. This is
  exact for the continuous risk-neutral model; the discretised schedule folds
  the continuous rate into the interior steps.
* :func:`ow_numeric` — minimise the discrete quadratic cost above under
  sum(q) = X (and q >= 0 via a small active-set loop), valid for any kernel
  (exponential or power-law). This is the ground truth the closed form is
  validated against in the tests.

The risk-averse extension of OW is *not* implemented; risk preferences enter
only through the Almgren–Chriss layer (documented in METHODOLOGY.md).
"""

from __future__ import annotations

import numpy as np

from .config import Config
from .impact import propagator_kernel


def ow_closed_form(X: float, T: float, rho: float, n_steps: int) -> np.ndarray:
    """Discretised OW schedule (shares per step, length n_steps, sums to X)."""
    if rho <= 0:
        raise ValueError("rho must be positive for the OW closed form")
    dt = T / n_steps
    block = X / (rho * T + 2.0)
    rate = rho * block  # shares per second in (0, T)
    q = np.full(n_steps, rate * dt)
    q[0] += block
    q[-1] += block
    return q


def cost_matrix(cfg: Config, n_steps: int, kind: str | None = None) -> np.ndarray:
    """Symmetric positive-definite matrix M with M_kj = G(|k-j| dt)."""
    dt = cfg.horizon_seconds / n_steps
    k = np.arange(n_steps)
    lag = np.abs(k[:, None] - k[None, :]) * dt
    kind = kind or cfg.impact.propagator
    return propagator_kernel(
        lag, kind, cfg.impact.resilience_rho, cfg.impact.powerlaw_beta, cfg.impact.powerlaw_tau0
    )


def transient_cost(cfg: Config, q: np.ndarray, kind: str | None = None) -> float:
    """Expected transient-impact cost 1/2 eta_t q' M q (currency)."""
    M = cost_matrix(cfg, len(q), kind)
    return 0.5 * cfg.impact.transient_eta * float(q @ M @ q)


def ow_numeric(
    cfg: Config,
    X: float | None = None,
    n_steps: int | None = None,
    kind: str | None = None,
) -> np.ndarray:
    """Cost-minimising schedule under sum(q) = X, q >= 0 (active-set KKT).

    For a PSD kernel matrix the equality-constrained minimiser is
    q = M^-1 1 * X / (1' M^-1 1); negative components (possible for
    power-law kernels) are pinned to zero and the reduced system re-solved.
    """
    X = cfg.initial_inventory if X is None else X
    n = n_steps or cfg.n_decision_steps
    M = cost_matrix(cfg, n, kind) + 1e-10 * np.eye(n)
    active = np.ones(n, dtype=bool)  # True = free variable
    for _ in range(n):
        idx = np.where(active)[0]
        Msub = M[np.ix_(idx, idx)]
        w = np.linalg.solve(Msub, np.ones(len(idx)))
        q_sub = w * (X / w.sum())
        if np.all(q_sub >= -1e-9 * X):
            q = np.zeros(n)
            q[idx] = np.maximum(q_sub, 0.0)
            # renormalise away the clip epsilon
            q *= X / q.sum()
            return q
        active[idx[q_sub < 0]] = False
    raise RuntimeError("active-set loop failed to converge")


def resilience_sweep(
    cfg: Config, rhos: tuple[float, ...] = (0.001, 0.01, 0.1)
) -> dict[float, dict[str, np.ndarray | float]]:
    """OW schedules and costs across resilience levels (Experiment D)."""
    out: dict[float, dict[str, np.ndarray | float]] = {}
    for rho in rhos:
        c = cfg.with_overrides({"impact": {"resilience_rho": rho, "propagator": "exponential"}})
        q_cf = ow_closed_form(c.initial_inventory, c.horizon_seconds, rho, c.n_decision_steps)
        q_num = ow_numeric(c)
        out[rho] = {
            "closed_form": q_cf,
            "numeric": q_num,
            "cost_closed_form": transient_cost(c, q_cf),
            "cost_numeric": transient_cost(c, q_num),
            "cost_twap": transient_cost(
                c, np.full(c.n_decision_steps, c.initial_inventory / c.n_decision_steps)
            ),
        }
    return out
