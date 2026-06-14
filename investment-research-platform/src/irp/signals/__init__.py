"""irp.signals — common signal schema + baseline signals.

Every signal is a standardized, comparable :class:`Signal` (see
:mod:`irp.signals.schema`): a cross-sectionally normalized score panel with a
category and direction. Baselines live in :mod:`irp.signals.baselines`, combination
and weight helpers in :mod:`irp.signals.normalize`, and a name→builder map in
:mod:`irp.signals.registry`.

Scores are built from features known at ``t``; use :meth:`Signal.lag` before
trading on the next bar so decisions never use same-bar information.
"""

from __future__ import annotations

from .baselines import (
    carry_signal,
    low_volatility_signal,
    macro_trend_signal,
    mean_reversion_signal,
    momentum_signal,
    quality_signal,
    trend_following_signal,
    value_signal,
)
from .normalize import combine, long_short_quantile, rank_xs, winsorize_xs, zscore_xs
from .registry import PLANNED, REGISTRY, available, get_signal
from .schema import Signal, SignalCategory, from_raw

__all__ = [
    "PLANNED",
    "REGISTRY",
    "Signal",
    "SignalCategory",
    "available",
    "carry_signal",
    "combine",
    "from_raw",
    "get_signal",
    "long_short_quantile",
    "low_volatility_signal",
    "macro_trend_signal",
    "mean_reversion_signal",
    "momentum_signal",
    "quality_signal",
    "rank_xs",
    "trend_following_signal",
    "value_signal",
    "winsorize_xs",
    "zscore_xs",
]
