"""Spread, depth and liquidity-stress dynamics shared by both simulators.

    spread_k = base_spread * f_time(k) * f_vol(sigma_k) * f_stress(z_k)

* ``f_time`` reuses the intraday U-shape (wide at the open/close).
* ``f_vol`` scales with the realised vol-regime ratio to a beta power.
* ``f_stress`` multiplies the spread in a persistent stressed regime.

Depth is lognormal around a configurable mean and mean-reverts via the
replenishment rate (used by the reactive LOB).
"""

from __future__ import annotations

import numpy as np

from .config import Config
from .price_process import u_shape_factor


def stress_paths(cfg: Config, rng: np.random.Generator, n_paths: int, n_steps: int) -> np.ndarray:
    """(n_paths, n_steps) 0/1 stressed-liquidity indicator (persistent)."""
    p_on = cfg.liquidity.stress_prob_per_step
    if p_on <= 0:
        return np.zeros((n_paths, n_steps))
    persist = 0.90
    u = rng.random((n_paths, n_steps))
    state = np.zeros((n_paths, n_steps))
    current = np.zeros(n_paths)
    for k in range(n_steps):
        turn_on = (current == 0) & (u[:, k] < p_on)
        stay_on = (current == 1) & (u[:, k] < persist)
        current = np.where(turn_on | stay_on, 1.0, 0.0)
        state[:, k] = current
    return state


def spread_paths(
    cfg: Config,
    rng: np.random.Generator,
    n_paths: int,
    n_steps: int | None = None,
    vol_ratio: np.ndarray | None = None,
    stress: np.ndarray | None = None,
) -> np.ndarray:
    """(n_paths, n_steps) full quoted spread in currency (>= one tick)."""
    n = n_steps or cfg.n_decision_steps
    base = cfg.spread_bps * 1e-4 * cfg.arrival_price
    f_time = u_shape_factor(n, cfg.vol_u_amplitude)[None, :]
    if vol_ratio is None:
        vol_ratio = np.ones((n_paths, n))
    f_vol = vol_ratio**cfg.liquidity.spread_vol_beta
    if stress is None:
        stress = stress_paths(cfg, rng, n_paths, n)
    f_stress = 1.0 + (cfg.liquidity.spread_stress_mult - 1.0) * stress
    noise = rng.lognormal(mean=-0.5 * 0.1**2, sigma=0.1, size=(n_paths, n))
    return np.maximum(base * f_time * f_vol * f_stress * noise, cfg.tick_size)


def initial_depth(cfg: Config, rng: np.random.Generator, size: int = 2) -> np.ndarray:
    """Lognormal L1 depth draw (shares); size 2 = (bid, ask)."""
    s = cfg.liquidity.depth_sigma
    return cfg.liquidity.depth_shares * rng.lognormal(mean=-0.5 * s * s, sigma=s, size=size)
