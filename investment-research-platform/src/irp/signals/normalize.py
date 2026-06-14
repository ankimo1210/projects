"""Cross-sectional standardization for signals.

These put every signal family on a common, comparable scale by transforming each
date's cross-section on its own (no time-axis look-ahead). They wrap the
feature-layer primitives so the two layers agree.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..features.price import cross_sectional_rank, cross_sectional_zscore


def zscore_xs(panel: pd.DataFrame, *, min_count: int = 3) -> pd.DataFrame:
    """Per-date cross-sectional z-score (mean 0, unit std within each date)."""
    return cross_sectional_zscore(panel, min_count=min_count)


def rank_xs(panel: pd.DataFrame, *, centered: bool = True) -> pd.DataFrame:
    """Per-date cross-sectional percentile rank.

    ``centered`` maps the [0, 1] rank to [-0.5, 0.5] so the neutral point is 0,
    matching the z-score convention (positive = above the cross-section).
    """
    r = cross_sectional_rank(panel, pct=True)
    return r - 0.5 if centered else r


def winsorize_xs(panel: pd.DataFrame, limit: float = 3.0) -> pd.DataFrame:
    """Clip standardized scores to ``[-limit, limit]`` to tame cross-sectional outliers."""
    return panel.clip(lower=-limit, upper=limit)


def combine(signals, weights=None, *, name: str = "composite", category=None):
    """Equal- or custom-weighted average of several signals' *oriented* scores.

    Because each input is already standardized and oriented (higher = prefer
    long), a weighted average is a valid composite. Returns a new
    :class:`~irp.signals.schema.Signal`. The union of dates/assets is used; cells
    missing in some signals are averaged over the present ones (no fabrication).
    """
    from .schema import Signal, SignalCategory

    sigs = list(signals)
    if not sigs:
        raise ValueError("combine() needs at least one signal")
    if weights is None:
        weights = [1.0] * len(sigs)
    if len(weights) != len(sigs):
        raise ValueError("weights length must match number of signals")

    oriented = [s.oriented * w for s, w in zip(sigs, weights, strict=True)]
    stacked = pd.concat(oriented)
    # mean over signals per (date, asset), skipping NaN so partial coverage still combines
    score = stacked.groupby(level=0).mean()
    score = score.sort_index()
    cat = category or SignalCategory.TREND
    meta = {"components": [s.name for s in sigs], "weights": list(weights)}
    return Signal(name, cat, score, direction=1, meta=meta)


def long_short_quantile(score: pd.DataFrame, quantile: float = 0.2) -> pd.DataFrame:
    """Map standardized scores to dollar-neutral long/short weights per date.

    Longs = top ``quantile`` of assets, shorts = bottom ``quantile``; each leg
    equal-weighted to gross 1.0 (net 0). NaNs are excluded from the ranking. This
    is a *research* convenience for inspecting a signal's spread — not a portfolio
    optimizer (that is Phase 2 portfolio construction).
    """
    weights = pd.DataFrame(0.0, index=score.index, columns=score.columns)
    for d, row in score.iterrows():
        valid = row.dropna()
        n = len(valid)
        if n < 2:
            continue
        k = max(1, int(np.floor(n * quantile)))
        ranked = valid.sort_values()
        shorts, longs = ranked.index[:k], ranked.index[-k:]
        weights.loc[d, longs] = 1.0 / len(longs)
        weights.loc[d, shorts] = -1.0 / len(shorts)
    return weights
