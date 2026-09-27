"""Offline market overview with honest pair counts and in-app alerts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import numpy as np
import pandas as pd

from .indicators import IndicatorInput


@dataclass(frozen=True, slots=True)
class OverviewResult:
    summary: pd.DataFrame
    correlations: pd.DataFrame
    pair_counts: pd.DataFrame
    alerts: pd.DataFrame
    correlation_window: int
    drawdown_alert: float
    zscore_alert: float
    mode: str
    currency: str
    adjustment: str


def market_overview(
    source: IndicatorInput,
    indicators: pd.DataFrame,
    *,
    correlation_window: int,
    drawdown_alert: float,
    zscore_alert: float,
) -> OverviewResult:
    """Rank available indicators and correlate only overlapping valid returns."""
    if source.mode != "retrospective":
        raise ValueError("market overview requires retrospective display history")
    if type(correlation_window) is not int or correlation_window < 3:
        raise ValueError("correlation window must contain at least three returns")
    if (
        isinstance(drawdown_alert, bool)
        or not isinstance(drawdown_alert, Real)
        or not math.isfinite(drawdown_alert)
        or not -1 <= drawdown_alert < 0
    ):
        raise ValueError("drawdown alert must be a finite negative fraction")
    if (
        isinstance(zscore_alert, bool)
        or not isinstance(zscore_alert, Real)
        or not math.isfinite(zscore_alert)
        or zscore_alert <= 0
    ):
        raise ValueError("zscore alert must be finite and positive")
    prices = source.prices
    if not isinstance(prices, pd.DataFrame) or prices.columns.empty:
        raise ValueError("overview prices are required")
    if (
        not isinstance(prices.index, pd.DatetimeIndex)
        or prices.index.tz is None
        or prices.index.has_duplicates
        or not prices.index.is_monotonic_increasing
        or prices.columns.has_duplicates
    ):
        raise ValueError("overview price axes must be unique, ordered and timezone-aware")
    if indicators.index.has_duplicates or set(indicators.index) != set(prices.columns):
        raise ValueError("overview indicator assets must match prices exactly")
    required = {
        "momentum",
        "drawdown",
        "zscore",
        "mode",
        "currency",
        "adjustment",
        "missing_reason",
        "quality_reasons",
    }
    if not required.issubset(indicators.columns):
        raise ValueError("overview indicators lack required fields")
    if (
        not indicators["mode"].eq(source.mode).all()
        or not indicators["currency"].eq(source.currency).all()
        or not indicators["adjustment"].eq(source.adjustment).all()
    ):
        raise ValueError("overview indicator provenance differs from price history")
    if any(not pd.api.types.is_numeric_dtype(dtype) for dtype in prices.dtypes):
        raise ValueError("overview prices must be numeric")
    numeric = prices.astype(float)
    values = numeric.to_numpy()
    if np.isinf(values).any() or (np.isfinite(values) & (values <= 0)).any():
        raise ValueError("overview prices must be positive finite values or missing")
    returns = numeric.pct_change(fill_method=None).iloc[-correlation_window:]
    valid = returns.notna().astype(int)
    pair_counts = valid.T.dot(valid)
    correlations = returns.corr(min_periods=3)
    summary = indicators.reindex(prices.columns).copy()
    summary["momentum_rank"] = summary["momentum"].rank(ascending=False, method="min")
    summary = summary.sort_values("momentum_rank", na_position="last")
    alerts = []
    for asset, row in summary.iterrows():
        reasons = tuple(
            dict.fromkeys((*source.quality_reasons.get(asset, ()), *row["quality_reasons"]))
        )
        for reason in reasons:
            alerts.append((asset, "quality", reason, float("nan")))
        missing = row["missing_reason"]
        if isinstance(missing, str) and missing:
            alerts.append((asset, "missing", missing, float("nan")))
        drawdown = row["drawdown"]
        if pd.notna(drawdown) and drawdown <= drawdown_alert:
            alerts.append((asset, "drawdown", "threshold", float(drawdown)))
        zscore = row["zscore"]
        if pd.notna(zscore) and abs(zscore) >= zscore_alert:
            alerts.append((asset, "zscore", "threshold", float(zscore)))
    alert_table = pd.DataFrame.from_records(
        alerts, columns=["instrument_id", "kind", "reason", "value"]
    )
    return OverviewResult(
        summary=summary,
        correlations=correlations,
        pair_counts=pair_counts,
        alerts=alert_table,
        correlation_window=correlation_window,
        drawdown_alert=float(drawdown_alert),
        zscore_alert=float(zscore_alert),
        mode=source.mode,
        currency=source.currency,
        adjustment=source.adjustment,
    )
