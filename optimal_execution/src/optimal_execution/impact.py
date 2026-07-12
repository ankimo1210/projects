"""Market-impact models: temporary, permanent, transient (+ square-root law).

Sign convention (see docs/METHODOLOGY.md): all impact quantities returned
here are *positive adverse magnitudes* in currency per share. The caller
applies the program sign: a sell executes at ``S0 - adverse``, a buy at
``S0 + adverse``. Executed quantities ``q >= 0`` are in shares per decision
step; trade rate ``v = q / dt`` in shares per second.

Channels
--------
temporary   concession = eta * v            (paid only while trading)
permanent   mid shift  = gamma * cum shares (never decays)
transient   displacement D with  D_{k+1} = exp(-rho dt) (D_k + eta_t q_k)
            — point-impulse convention: a trade at t pushes D up by eta_t q
            and the push decays over the following interval, exactly as in
            continuous-time OW. (The task prompt's written recursion adds the
            newest impulse undecayed; that variant makes adjacent-step trades
            interact at full strength, so the discrete scheduling QP becomes
            indefinite/ill-posed. See docs/NUMERICAL_METHODS.md.)
            Execution at step k sees the pre-trade displacement D_k plus half
            of its own jump 0.5 eta_t q_k (block-average through the book).
propagator  D_k = sum_{j<k} G((k-j) dt) eta_t q_j  for exponential or
            power-law G — generalises the exponential recursion.
square-root I(Q) = Y sigma_day sqrt(Q / ADV)  (diagnostic only; a
            concave *total* impact law, not additive with the linear model)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config


@dataclass(frozen=True)
class ImpactChannels:
    """Which impact channels are active in a classical-world simulation."""

    temporary: bool = True
    permanent: bool = True
    transient: bool = False

    @staticmethod
    def named(name: str) -> ImpactChannels:
        presets = {
            "temporary_only": ImpactChannels(True, False, False),
            "permanent_only": ImpactChannels(False, True, False),
            "transient_only": ImpactChannels(False, False, True),
            "temporary_permanent": ImpactChannels(True, True, False),
            "all": ImpactChannels(True, True, True),
        }
        return presets[name]


def temporary_concession(v: np.ndarray | float, eta: float) -> np.ndarray | float:
    """Instantaneous price concession eta * v (currency/share), v in shares/s."""
    return eta * np.asarray(v)


def temporary_cost(q: np.ndarray | float, dt: float, eta: float) -> np.ndarray | float:
    """Cash cost of temporary impact for a block q over dt: eta * q^2 / dt."""
    q = np.asarray(q)
    return eta * q * q / dt


def transient_displacement(
    q: np.ndarray, dt: float, eta_t: float, rho: float
) -> tuple[np.ndarray, np.ndarray]:
    """Pre-trade transient displacement per step and the post-horizon state.

    Parameters
    ----------
    q : (..., n_steps) executed shares per step (non-negative).

    Returns
    -------
    d_pre : same shape as q — displacement *seen by* the trade at each step
            (i.e. the state before that step's trade).
    d_end : (...,) displacement after the final step (for recovery plots).
    """
    orig_shape = np.asarray(q).shape
    q2 = np.atleast_2d(np.asarray(q, dtype=float))
    n_paths, n_steps = q2.shape
    decay = float(np.exp(-rho * dt))
    d_pre = np.empty_like(q2)
    d = np.zeros(n_paths)
    for k in range(n_steps):
        d_pre[:, k] = d
        d = decay * (d + eta_t * q2[:, k])
    if len(orig_shape) == 1:
        return d_pre[0], d[0]
    return d_pre, d


def transient_decay_curve(d0: float, rho: float, dt: float, n_steps: int) -> np.ndarray:
    """Displacement decay after trading stops: d0 * exp(-rho * k * dt)."""
    return d0 * np.exp(-rho * dt * np.arange(n_steps + 1))


def propagator_kernel(
    tau: np.ndarray, kind: str, rho: float, beta: float, tau0: float
) -> np.ndarray:
    """Decay kernel G(tau) with G(0) = 1."""
    tau = np.asarray(tau, dtype=float)
    if kind == "exponential":
        return np.exp(-rho * tau)
    if kind == "powerlaw":
        return (1.0 + tau / tau0) ** (-beta)
    raise ValueError(f"unknown propagator kind {kind!r}")


def propagator_matrix(n_steps: int, dt: float, cfg: Config, kind: str | None = None) -> np.ndarray:
    """Strictly-lower-triangular matrix P with P[k, j] = G((k - j) dt), j < k.

    Point-impulse lag convention: the displacement of an impulse at step j
    seen by step k has decayed for (k - j) intervals, matching the recursion
    D_{k+1} = e^{-rho dt} (D_k + eta q_k) exactly for the exponential kernel.
    """
    kind = kind or cfg.impact.propagator
    k = np.arange(n_steps)
    lag = (k[:, None] - k[None, :]) * dt
    g = propagator_kernel(
        np.maximum(lag, 0.0),
        kind,
        cfg.impact.resilience_rho,
        cfg.impact.powerlaw_beta,
        cfg.impact.powerlaw_tau0,
    )
    return np.where(lag > 0, g, 0.0)


def propagator_displacement(
    q: np.ndarray, dt: float, cfg: Config, kind: str | None = None
) -> np.ndarray:
    """Pre-trade displacement via the generic propagator, shape of q."""
    q2 = np.atleast_2d(np.asarray(q, dtype=float))
    P = propagator_matrix(q2.shape[1], dt, cfg, kind)
    d = cfg.impact.transient_eta * q2 @ P.T
    return d.reshape(np.asarray(q).shape)


def sqrt_impact(Q: np.ndarray | float, cfg: Config) -> np.ndarray | float:
    """Square-root law I(Q) = Y sigma_day sqrt(Q/ADV), currency per share."""
    Q = np.asarray(Q, dtype=float)
    return cfg.impact.sqrt_impact_Y * cfg.sigma_daily * np.sqrt(Q / cfg.average_daily_volume)


def classical_execution(
    cfg: Config,
    q: np.ndarray,
    mid_paths: np.ndarray,
    spreads: np.ndarray | None = None,
    channels: ImpactChannels | None = None,
) -> dict[str, np.ndarray]:
    """Apply impact models to schedules against unaffected mid paths.

    Parameters
    ----------
    q         : (n_paths, n_steps) executed shares per step, >= 0.
    mid_paths : (n_paths, n_steps + 1) unaffected mid; column k is the price
                at the *start* of step k (column 0 = arrival price).
    spreads   : (n_paths, n_steps) full quoted spread in currency, or None
                for the configured constant average spread.

    Returns per-step arrays (all (n_paths, n_steps), currency per share,
    positive = adverse): ``exec_price``, ``spread_cost``, ``temporary``,
    ``permanent``, ``transient``, ``fee`` plus ``impacted_mid`` (mid including
    permanent + transient state, for plotting) and ``d_end`` (n_paths,).
    """
    q = np.asarray(q, dtype=float)
    channels = channels or ImpactChannels()
    n_paths, n_steps = q.shape
    dt = cfg.horizon_seconds / n_steps
    s = cfg.sign
    imp = cfg.impact

    if spreads is None:
        spreads = np.full((n_paths, n_steps), 2.0 * cfg.half_spread)
    spread_cost = 0.5 * spreads

    temp = imp.temporary_eta * (q / dt) if channels.temporary else np.zeros_like(q)

    if channels.permanent:
        cum_prev = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(q, axis=1)[:, :-1]], axis=1)
        perm = imp.permanent_gamma * (cum_prev + 0.5 * q)
        perm_mid = imp.permanent_gamma * cum_prev
    else:
        perm = np.zeros_like(q)
        perm_mid = np.zeros_like(q)

    if channels.transient:
        d_pre, d_end = transient_displacement(q, dt, imp.transient_eta, imp.resilience_rho)
        trans = d_pre + 0.5 * imp.transient_eta * q
    else:
        d_pre = np.zeros_like(q)
        d_end = np.zeros(n_paths)
        trans = np.zeros_like(q)

    fee = np.full_like(q, cfg.fee_per_share)

    step_mid = mid_paths[:, :-1]
    adverse = spread_cost + temp + perm + trans
    exec_price = step_mid - s * adverse
    impacted_mid = step_mid - s * (perm_mid + d_pre)

    return {
        "exec_price": exec_price,
        "spread_cost": spread_cost,
        "temporary": temp,
        "permanent": perm,
        "transient": trans,
        "fee": fee,
        "impacted_mid": impacted_mid,
        "d_pre": d_pre,
        "d_end": d_end,
    }
