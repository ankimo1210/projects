"""Intraday market volume: deterministic profile and stochastic realisation."""

from __future__ import annotations

import numpy as np

from .config import Config
from .price_process import u_shape_factor


def volume_weights(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    """Mean-one per-step volume weights (flat or U-shaped)."""
    n = n_steps or cfg.n_decision_steps
    if cfg.volume_profile == "u_shape":
        return u_shape_factor(n, cfg.volume_u_amplitude)
    return np.ones(n)


def expected_step_volume(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    """Expected market volume per decision step, shares."""
    n = n_steps or cfg.n_decision_steps
    dt = cfg.horizon_seconds / n
    return cfg.market_volume_rate * dt * volume_weights(cfg, n)


def vwap_weights(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    """Expected-volume weights normalised to sum to one (VWAP schedule)."""
    ev = expected_step_volume(cfg, n_steps)
    return ev / ev.sum()


def simulate_step_volumes(
    cfg: Config,
    rng: np.random.Generator,
    n_paths: int,
    n_steps: int | None = None,
) -> np.ndarray:
    """Realised market volume per step, shape (n_paths, n_steps), shares.

    Lognormal multiplicative noise with mean one around the expected profile.
    """
    n = n_steps or cfg.n_decision_steps
    ev = expected_step_volume(cfg, n)[None, :]
    s = cfg.volume_mult_sigma
    if s <= 0:
        return np.broadcast_to(ev, (n_paths, n)).copy()
    mult = rng.lognormal(mean=-0.5 * s * s, sigma=s, size=(n_paths, n))
    return ev * mult
