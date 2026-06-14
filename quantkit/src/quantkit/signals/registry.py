"""Signal registry — name → builder, so notebooks/backtests can iterate signals.

All six families (trend/value/quality/carry/risk/macro) are registered. Price-only
families (momentum/trend/low-vol/mean-reversion) take a price panel; the
fundamentals/yield families (value/quality/carry) take a cross-sectional *metric*
panel; macro_trend takes a point-in-time macro level.
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
    "value": baselines.value_signal,
    "quality": baselines.quality_signal,
    "carry": baselines.carry_signal,
}

#: kept for backward-compatibility; all families are now implemented
PLANNED: dict[str, Callable[..., Signal]] = {}


def get_signal(name: str) -> Callable[..., Signal]:
    """Return a signal builder by name."""
    if name in REGISTRY:
        return REGISTRY[name]
    raise KeyError(f"unknown signal {name!r}; available: {sorted(REGISTRY)}")


def available() -> list[str]:
    """Names of all registered signals (all six families)."""
    return sorted(REGISTRY)
