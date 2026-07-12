"""Execution strategies: classical-world schedules and LOB-world policies.

Classical world (vectorised Monte Carlo): a strategy is a matrix of child
orders q (n_paths, n_steps). Deterministic schedules broadcast one row;
volume-dependent schedules (VWAP realised, POV) map realised volumes to
quantities path by path.

LOB world: a strategy is a policy object with ``reset()`` and
``__call__(obs, env) -> action`` where the action is either a discrete index
(RL grid) or a dict {"market_qty", "limit", "limit_qty"} routed through the
same safety layer. Schedule-following policies carry over any clipped
shortfall to later steps so hard caps do not silently strand inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .almgren_chriss import ac_schedule
from .config import Config
from .environment import ExecutionEnv
from .fills import passive_fill_probability
from .resilience import ow_numeric
from .volume import vwap_weights

CLASSICAL_STRATEGY_IDS = ("immediate", "twap", "vwap", "pov", "ac", "ow")
LOB_STRATEGY_IDS = (
    "twap_mkt",
    "ac_mkt",
    "pov_mkt",
    "limit_only",
    "heuristic",
)


# --------------------------------------------------------------------------
# classical-world schedules
# --------------------------------------------------------------------------
def schedule_immediate(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    n = n_steps or cfg.n_decision_steps
    q = np.zeros(n)
    q[0] = cfg.initial_inventory
    return q


def schedule_twap(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    n = n_steps or cfg.n_decision_steps
    return np.full(n, cfg.initial_inventory / n)


def schedule_vwap(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    return cfg.initial_inventory * vwap_weights(cfg, n_steps)


def schedule_ac(cfg: Config, n_steps: int | None = None, lam: float | None = None) -> np.ndarray:
    n = n_steps or cfg.n_decision_steps
    lam = cfg.risk_aversion_lambda if lam is None else lam
    kappa = float(np.sqrt(lam * cfg.sigma_abs**2 / cfg.impact.temporary_eta))
    return ac_schedule(cfg.initial_inventory, cfg.horizon_seconds, kappa, n)


def schedule_ow(cfg: Config, n_steps: int | None = None) -> np.ndarray:
    return ow_numeric(cfg, n_steps=n_steps)


def schedule_pov(cfg: Config, volumes: np.ndarray, rate: float | None = None) -> np.ndarray:
    """Participation-of-volume schedule per path (needs realised volumes).

    q_t = rate * V_t capped by remaining inventory; whatever is left at the
    final step is executed there (deadline cleanup — visible in the TCA).
    """
    p = cfg.max_participation_rate if rate is None else rate
    n_paths, n_steps = volumes.shape
    q = np.zeros_like(volumes)
    remaining = np.full(n_paths, cfg.initial_inventory)
    for k in range(n_steps):
        take = np.minimum(p * volumes[:, k], remaining)
        if k == n_steps - 1:
            take = remaining
        q[:, k] = take
        remaining = remaining - take
    return q


def classical_schedules(cfg: Config, volumes: np.ndarray) -> dict[str, np.ndarray]:
    """All classical strategies as (n_paths, n_steps) matrices."""
    n_paths, n_steps = volumes.shape
    ones = np.ones((n_paths, 1))
    return {
        "immediate": ones * schedule_immediate(cfg, n_steps)[None, :],
        "twap": ones * schedule_twap(cfg, n_steps)[None, :],
        "vwap": ones * schedule_vwap(cfg, n_steps)[None, :],
        "pov": schedule_pov(cfg, volumes),
        "ac": ones * schedule_ac(cfg, n_steps)[None, :],
        "ow": ones * schedule_ow(cfg, n_steps)[None, :],
    }


# --------------------------------------------------------------------------
# LOB-world policies
# --------------------------------------------------------------------------
class Policy(Protocol):  # pragma: no cover - typing helper
    def reset(self) -> None: ...

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> int | dict[str, Any]: ...


@dataclass
class MarketSchedulePolicy:
    """Follow a fixed schedule with market orders; carry clipped shortfall."""

    schedule: np.ndarray
    behind: float = 0.0
    _planned: float = 0.0

    def reset(self) -> None:
        self.behind = 0.0
        self._planned = 0.0

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> dict[str, Any]:
        k = env.k
        self._planned += float(self.schedule[k])
        executed = env.cfg.initial_inventory - env.x
        want = max(self._planned - executed, 0.0)
        return {"market_qty": want, "limit": "none"}


@dataclass
class POVPolicy:
    """Adaptive participation-of-volume using the environment's volume EMA."""

    rate: float

    def reset(self) -> None:  # stateless
        return

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> dict[str, Any]:
        want = self.rate * env.vol_ema
        return {"market_qty": min(want, env.x), "limit": "none"}


@dataclass
class LimitOnlyPolicy:
    """Always rest a passive order at the touch; never crosses the spread.

    Demonstrates fill risk: unfilled remainder hits the forced terminal
    liquidation, which the TCA reports as cleanup cost.
    """

    qty_mult: float = 1.5

    def reset(self) -> None:
        return

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> dict[str, Any]:
        n_left = env.N - env.k
        slice_target = env.x / max(n_left, 1)
        return {
            "market_qty": 0.0,
            "limit": "join",
            "limit_qty": min(self.qty_mult * slice_target, env.x),
        }


@dataclass
class MixedHeuristicPolicy:
    """Tactical rule combining pace urgency, spread, imbalance and fill odds.

    * behind pace -> market orders to catch up (aggressively near deadline);
    * otherwise rest passive quantity, improving the quote when the spread is
      wide and the book/imbalance makes a fill likely.
    """

    pace_tolerance: float = 0.05
    improve_spread_ticks: float = 3.0

    def reset(self) -> None:
        return

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> dict[str, Any]:
        cfg = env.cfg
        assert env.book is not None
        k, N = env.k, env.N
        x_frac = env.x / cfg.initial_inventory
        time_left_frac = 1.0 - k / N
        behind = x_frac - time_left_frac  # >0: behind TWAP pace
        slice_twap = cfg.initial_inventory / N

        market_qty = 0.0
        if N - k <= 2:
            market_qty = env.x / max(N - k, 1) * 1.2
        elif behind > self.pace_tolerance:
            market_qty = slice_twap * (1.0 + 8.0 * behind)

        book = env.book
        sign = cfg.sign
        opp_depth = book.ask_depth if sign > 0 else book.bid_depth
        # favourable flow for a seller: buy pressure (positive imbalance)
        fav_imb = sign * book.imbalance
        p_fill = passive_fill_probability(
            queue_ahead=opp_depth,
            order_qty=slice_twap,
            opposite_rate_per_s=cfg.mo_rate_per_side * (1.0 + 0.5 * fav_imb),
            mean_order_size=cfg.lob.market_order_size_mean,
            horizon_s=env.dt,
        )
        spread_ticks = book.spread / cfg.tick_size
        improve = spread_ticks >= self.improve_spread_ticks and fav_imb > -0.2
        limit_mode = "improve" if improve else "join"
        limit_qty = min(slice_twap * (1.0 + p_fill), max(env.x - market_qty, 0.0))
        if limit_qty < 1.0:
            limit_mode = "none"
            limit_qty = 0.0
        return {"market_qty": market_qty, "limit": limit_mode, "limit_qty": limit_qty}


def lob_policies(cfg: Config) -> dict[str, Policy]:
    """The scripted LOB-world strategy set (RL policies are added separately)."""
    return {
        "twap_mkt": MarketSchedulePolicy(schedule_twap(cfg)),
        "ac_mkt": MarketSchedulePolicy(schedule_ac(cfg)),
        "pov_mkt": POVPolicy(rate=cfg.max_participation_rate * 0.75),
        "limit_only": LimitOnlyPolicy(),
        "heuristic": MixedHeuristicPolicy(),
    }
