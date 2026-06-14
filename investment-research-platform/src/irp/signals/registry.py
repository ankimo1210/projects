"""Signal registry — name → builder, so notebooks/backtests can iterate signals.

Implemented baselines are registered; the not-yet-wired families are listed
separately so callers can see the intended breadth (and get a clear error rather
than a missing key) until their data connectors land.
"""

from __future__ import annotations

from collections.abc import Callable

from . import baselines
from .schema import Signal

REGISTRY: dict[str, Callable[..., Signal]] = {
    "momentum": baselines.momentum_signal,
    "trend_following": baselines.trend_following_signal,
    "low_volatility": baselines.low_volatility_signal,
    "mean_reversion": baselines.mean_reversion_signal,
    "macro_trend": baselines.macro_trend_signal,
}

#: registered but data-gated — calling these raises NotImplementedError (Phase 2)
PLANNED: dict[str, Callable[..., Signal]] = {
    "value": baselines.value_signal,
    "quality": baselines.quality_signal,
    "carry": baselines.carry_signal,
}


def get_signal(name: str) -> Callable[..., Signal]:
    """Return a signal builder by name (implemented or planned)."""
    if name in REGISTRY:
        return REGISTRY[name]
    if name in PLANNED:
        return PLANNED[name]
    raise KeyError(
        f"unknown signal {name!r}; available: {sorted(REGISTRY)} (planned: {sorted(PLANNED)})"
    )


def available() -> list[str]:
    """Names of signals that are actually implemented."""
    return sorted(REGISTRY)
