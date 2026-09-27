"""Price indicators with explicit input provenance."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC

import numpy as np
import pandas as pd

from market_research.contracts import ADJUSTMENTS

from .dataset import PriceDataset


@dataclass(frozen=True, slots=True)
class IndicatorInput:
    prices: pd.DataFrame
    mode: str
    currency: str
    adjustment: str
    quality_reasons: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    missing_by_asset: Mapping[str, str] = field(default_factory=dict)


def indicator_table(
    source: IndicatorInput, *, momentum_window: int, volatility_window: int
) -> pd.DataFrame:
    """Calculate current indicators without filling missing observations."""
    prices = source.prices
    if momentum_window < 1 or volatility_window < 2:
        raise ValueError("momentum window must be positive and volatility window at least two")
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.tz is None:
        raise ValueError("price index must be timezone-aware")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("price index must be unique and ordered")
    if prices.columns.has_duplicates or not len(prices.columns):
        raise ValueError("price columns must be unique and nonempty")
    if source.mode not in {"retrospective", "point_in_time"}:
        raise ValueError("invalid indicator mode")
    if not source.currency or source.adjustment not in ADJUSTMENTS:
        raise ValueError("currency and adjustment are required")
    try:
        values = prices.to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("prices must be positive numeric values or missing") from exc
    if (np.isfinite(values) & (values <= 0)).any() or np.isinf(values).any():
        raise ValueError("prices must be positive finite values or missing")

    result = pd.DataFrame(index=prices.columns)
    if prices.empty:
        for name in (
            "latest_close",
            "momentum",
            "volatility_annualized",
            "drawdown",
            "zscore",
        ):
            result[name] = np.nan
        result["mode"] = source.mode
        result["currency"] = source.currency
        result["adjustment"] = source.adjustment
        result["quality_reasons"] = [
            source.quality_reasons.get(asset, ()) for asset in prices.columns
        ]
        result["missing_reason"] = [
            source.missing_by_asset.get(asset, "missing_price") for asset in prices.columns
        ]
        return result

    returns = prices.pct_change(fill_method=None)
    momentum = prices.pct_change(periods=momentum_window, fill_method=None).iloc[-1]
    volatility = returns.rolling(volatility_window, min_periods=volatility_window).std(ddof=1).iloc[
        -1
    ] * math.sqrt(252)
    latest = prices.iloc[-1]
    rolling = prices.rolling(momentum_window, min_periods=momentum_window)
    zscore = (latest - rolling.mean().iloc[-1]) / rolling.std(ddof=0).iloc[-1].replace(0, np.nan)
    result["latest_close"] = latest
    result["momentum"] = momentum
    result["volatility_annualized"] = volatility
    result["drawdown"] = latest / prices.cummax().iloc[-1] - 1
    result["zscore"] = zscore
    for asset in source.missing_by_asset:
        if asset in result.index:
            result.loc[
                asset,
                ["latest_close", "momentum", "volatility_annualized", "drawdown", "zscore"],
            ] = np.nan
    result["mode"] = source.mode
    result["currency"] = source.currency
    result["adjustment"] = source.adjustment
    result["quality_reasons"] = [source.quality_reasons.get(asset, ()) for asset in prices.columns]
    reasons = []
    for asset in prices.columns:
        reason = source.missing_by_asset.get(asset, "")
        if not reason and pd.isna(latest[asset]):
            reason = "missing_price"
        if not reason and len(prices) <= max(momentum_window, volatility_window):
            reason = "insufficient_history"
        if not reason and (pd.isna(momentum[asset]) or pd.isna(volatility[asset])):
            reason = "missing_price"
        if not reason and pd.isna(zscore[asset]):
            reason = "constant_window"
        reasons.append(reason)
    result["missing_reason"] = reasons
    return result


def close_history(dataset: PriceDataset) -> IndicatorInput:
    """Align daily display rows by session date at the latest constituent close."""
    if dataset.as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    rows = []
    latest_bars = {}
    seen = set()
    providers = {}
    for bar in dataset.bars:
        asset = bar.instrument.instrument_id
        if bar.available_at > dataset.as_of or bar.observed_at > dataset.as_of:
            raise ValueError(f"future bar in display history for {asset}")
        if not bar.is_final:
            raise ValueError(f"non_final bar in display history for {asset}")
        if bar.instrument.currency != dataset.currency:
            raise ValueError(f"currency mismatch for {asset}")
        if bar.adjustment != dataset.adjustment:
            raise ValueError(f"adjustment mismatch for {asset}")
        if asset in providers and providers[asset] != bar.provider:
            raise ValueError(f"provider mixing for {asset}")
        providers[asset] = bar.provider
        key = (asset, bar.session_date)
        if key in seen:
            raise ValueError(f"duplicate displayed close for {asset}")
        seen.add(key)
        rows.append(
            {
                "session_date": bar.session_date,
                "bar_end": bar.bar_end,
                "asset": asset,
                "close": np.nan if bar.quality == "reject" else bar.close,
            }
        )
        if asset not in latest_bars or latest_bars[asset].bar_end < bar.bar_end:
            latest_bars[asset] = bar
    if rows:
        frame = pd.DataFrame(rows)
        row_times = frame.groupby("session_date")["bar_end"].max().sort_index()
        prices = frame.pivot(index="session_date", columns="asset", values="close").sort_index()
        prices.index = pd.DatetimeIndex(row_times.tolist()).tz_convert(UTC)
        extra_assets = sorted(
            (
                {gap.instrument.instrument_id for gap in dataset.gaps}
                | {exclusion.bar.instrument.instrument_id for exclusion in dataset.exclusions}
            )
            - set(prices.columns)
        )
        prices = prices.reindex(columns=[*prices.columns, *extra_assets])
    else:
        assets = {gap.instrument.instrument_id for gap in dataset.gaps} | {
            exclusion.bar.instrument.instrument_id for exclusion in dataset.exclusions
        }
        prices = pd.DataFrame(index=pd.DatetimeIndex([], tz=UTC), columns=sorted(assets))
    quality_reasons = {asset: bar.quality_reasons for asset, bar in latest_bars.items()}
    missing_by_asset = {
        asset: "rejected_price" for asset, bar in latest_bars.items() if bar.quality == "reject"
    }
    for gap in dataset.gaps:
        asset = gap.instrument.instrument_id
        latest_bar = latest_bars.get(asset)
        if latest_bar is None or gap.session_date >= latest_bar.session_date:
            missing_by_asset[asset] = "gap"
    for exclusion in dataset.exclusions:
        asset = exclusion.bar.instrument.instrument_id
        latest_bar = latest_bars.get(asset)
        if latest_bar is None or exclusion.bar.bar_end >= latest_bar.bar_end:
            missing_by_asset[asset] = exclusion.reason
    return IndicatorInput(
        prices,
        dataset.mode,
        dataset.currency,
        dataset.adjustment,
        quality_reasons,
        missing_by_asset,
    )
