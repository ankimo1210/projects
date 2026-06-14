"""quantkit.regime — causal market-regime detection (volatility states, trend).

Labels are point-in-time: the regime at date ``t`` uses only data through ``t``
(expanding vol quantiles, trailing moving averages), so a backtest can condition on
them without look-ahead. See :mod:`quantkit.regime.detect`.
"""

from __future__ import annotations

from .detect import regime_summary, trend_regime, vol_regime

__all__ = ["regime_summary", "trend_regime", "vol_regime"]
