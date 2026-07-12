"""Unaffected mid-price process.

Arithmetic (absolute) Brownian dynamics on the decision grid:

    S0_{k+1} = S0_k + alpha_k * dt + sigma_k * sqrt(dt) * Z_k  (+ jumps)

with sigma in currency / share / sqrt(second). Optional features: intraday
U-shaped volatility, a two-state stochastic-volatility regime, compound
Poisson jumps, and a decaying deterministic alpha (drift) used for
adverse-selection stress tests. The *unaffected* price never includes the
agent's own impact — impacted prices are built on top by the simulators.
"""

from __future__ import annotations

import numpy as np

from .config import Config


def u_shape_factor(n_steps: int, amplitude: float) -> np.ndarray:
    """Mean-one U-shaped multiplier evaluated at step midpoints."""
    t = (np.arange(n_steps) + 0.5) / n_steps  # in (0, 1)
    u = 1.0 + amplitude * ((2.0 * t - 1.0) ** 2 - 1.0 / 3.0)
    return u / u.mean()


def sigma_profile(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    """Deterministic sigma_k (currency/share/sqrt(s)) per decision step."""
    n = n_steps or cfg.n_decision_steps
    base = np.full(n, cfg.sigma_abs)
    if cfg.vol_profile == "u_shape":
        base = base * u_shape_factor(n, cfg.vol_u_amplitude)
    return base


def alpha_profile(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    """Deterministic drift alpha_k in currency / share / second per step."""
    n = n_steps or cfg.n_decision_steps
    if not cfg.alpha.enabled:
        return np.zeros(n)
    dt = cfg.horizon_seconds / n
    t = (np.arange(n) + 0.5) * dt
    drift_per_second = cfg.alpha.drift_bps_per_hour * 1e-4 * cfg.arrival_price / 3600.0
    return drift_per_second * np.exp(-t / cfg.alpha.decay_seconds)


def simulate_vol_regime(
    cfg: Config, rng: np.random.Generator, n_paths: int, n_steps: int
) -> np.ndarray:
    """(n_paths, n_steps) multiplicative vol-regime factor (1 or regime mult)."""
    sv = cfg.stochastic_vol
    if not sv.enabled:
        return np.ones((n_paths, n_steps))
    switches = rng.random((n_paths, n_steps)) < sv.switch_prob_per_step
    state = np.zeros((n_paths, n_steps), dtype=bool)
    current = np.zeros(n_paths, dtype=bool)
    for k in range(n_steps):
        current = np.where(switches[:, k], ~current, current)
        state[:, k] = current
    return np.where(state, sv.regime_vol_mult, 1.0)


def simulate_mid_paths(
    cfg: Config,
    rng: np.random.Generator,
    n_paths: int,
    n_steps: int | None = None,
) -> np.ndarray:
    """Simulate unaffected mid paths, shape (n_paths, n_steps + 1).

    Column 0 is the arrival price. Uses the decision grid dt = T / n_steps.
    """
    n = n_steps or cfg.n_decision_steps
    dt = cfg.horizon_seconds / n
    sig = sigma_profile(cfg, n)[None, :] * simulate_vol_regime(cfg, rng, n_paths, n)
    alpha = alpha_profile(cfg, n)[None, :]

    increments = alpha * dt + sig * np.sqrt(dt) * rng.standard_normal((n_paths, n))

    if cfg.jumps.enabled:
        lam = cfg.jumps.intensity_per_hour * dt / 3600.0
        counts = rng.poisson(lam, size=(n_paths, n))
        jump_scale = cfg.jumps.jump_sigma_bps * 1e-4 * cfg.arrival_price
        jumps = jump_scale * np.sqrt(np.maximum(counts, 0)) * rng.standard_normal((n_paths, n))
        increments = increments + np.where(counts > 0, jumps, 0.0)

    paths = np.empty((n_paths, n + 1))
    paths[:, 0] = cfg.arrival_price
    np.cumsum(increments, axis=1, out=paths[:, 1:])
    paths[:, 1:] += cfg.arrival_price
    return paths
