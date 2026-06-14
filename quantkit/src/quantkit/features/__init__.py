"""quantkit.features — causal feature engineering for prices and macro.

Price features (``quantkit.features.price``) are strictly trailing/cross-sectional, so
``feature[t]`` depends only on data at or before ``t``. Macro features
(``quantkit.features.macro``) are point-in-time via :func:`quantkit.macro.store.as_of`. The
no-look-ahead invariant is enforced by ``tests/test_features.py``.
"""

from __future__ import annotations

from .macro import pit_change, pit_feature_frame, pit_level, pit_zscore
from .price import (
    cross_sectional_rank,
    cross_sectional_zscore,
    cumulative_return,
    drawdown,
    ewma_volatility,
    ma_ratio,
    momentum,
    moving_average,
    realized_volatility,
    returns,
    rolling_volatility,
    rolling_zscore,
    rsi,
)

__all__ = [
    "cross_sectional_rank",
    "cross_sectional_zscore",
    "cumulative_return",
    "drawdown",
    "ewma_volatility",
    "ma_ratio",
    "momentum",
    "moving_average",
    "pit_change",
    "pit_feature_frame",
    "pit_level",
    "pit_zscore",
    "realized_volatility",
    "returns",
    "rolling_volatility",
    "rolling_zscore",
    "rsi",
]
