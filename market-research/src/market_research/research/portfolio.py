"""Virtual long-only allocation risk from complete saved price windows."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np
import pandas as pd

from .indicators import IndicatorInput


@dataclass(frozen=True, slots=True)
class VirtualConstraints:
    max_gross: float = 1.0
    max_name_weight: float = 1.0
    cash_min: float = 0.0

    def __post_init__(self) -> None:
        for name in ("max_gross", "max_name_weight", "cash_min"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite numeric")
        if not 0 < self.max_gross <= 1:
            raise ValueError("max_gross must be in (0, 1]")
        if not 0 < self.max_name_weight <= 1:
            raise ValueError("max_name_weight must be in (0, 1]")
        if not 0 <= self.cash_min < 1:
            raise ValueError("cash_min must be in [0, 1)")


@dataclass(frozen=True, slots=True)
class VirtualRiskResult:
    weights: pd.Series
    cash_weight: float
    total_vol_annualized: float
    component_vol_annualized: pd.Series
    covariance_daily: pd.DataFrame
    base_currency: str
    adjustment: str
    mode: str
    lookback: int
    periods_per_year: int
    start_at: pd.Timestamp
    end_at: pd.Timestamp
    quality_reasons: Mapping[str, tuple[str, ...]]


def virtual_risk_report(
    source: IndicatorInput,
    weights: pd.Series,
    *,
    base_currency: str,
    lookback: int,
    periods_per_year: int,
    constraints: VirtualConstraints = VirtualConstraints(),
) -> VirtualRiskResult:
    """Annualize sample-covariance risk without filling missing prices or weights."""
    if source.mode != "retrospective":
        raise ValueError("virtual risk requires retrospective display prices")
    if not isinstance(base_currency, str) or base_currency.strip().upper() != source.currency:
        raise ValueError(
            "risk base currency must match price currency; FX conversion is unavailable"
        )
    if type(lookback) is not int or lookback < 2:
        raise ValueError("lookback must contain at least two returns")
    if type(periods_per_year) is not int or periods_per_year <= 0:
        raise ValueError("periods_per_year must be a positive integer")
    if not isinstance(constraints, VirtualConstraints):
        raise ValueError("virtual constraints are required")
    prices = source.prices
    if not isinstance(prices, pd.DataFrame) or prices.columns.empty:
        raise ValueError("price assets are required")
    if prices.columns.has_duplicates:
        raise ValueError("price asset columns must be unique")
    if (
        not isinstance(prices.index, pd.DatetimeIndex)
        or prices.index.tz is None
        or prices.index.has_duplicates
        or not prices.index.is_monotonic_increasing
    ):
        raise ValueError("price timestamps must be timezone-aware, unique and ordered")
    if len(prices) < lookback + 1:
        raise ValueError("insufficient price history for risk lookback")
    if not isinstance(weights, pd.Series) or weights.index.has_duplicates:
        raise ValueError("one explicit weight per asset is required")
    if set(weights.index) != set(prices.columns):
        raise ValueError("weights must cover exactly the price assets")
    ordered = weights.reindex(prices.columns)
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in ordered):
        raise ValueError("weights must be numeric")
    w = ordered.astype(float)
    if not np.isfinite(w.to_numpy()).all() or (w < 0).any():
        raise ValueError("long-only weights must be finite and nonnegative")
    if (w > constraints.max_name_weight + 1e-12).any():
        raise ValueError("weight exceeds per-name limit")
    gross = float(math.fsum(w))
    if gross > constraints.max_gross + 1e-12 or gross > 1 - constraints.cash_min + 1e-12:
        raise ValueError("weights exceed gross or cash constraint")

    window = prices.iloc[-(lookback + 1) :].reindex(columns=w.index)
    if window.isna().to_numpy().any():
        raise ValueError("missing price in risk lookback")
    if any(
        isinstance(value, bool) or not isinstance(value, Real) for value in window.to_numpy().flat
    ):
        raise ValueError("prices must be numeric")
    numeric = window.astype(float)
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("nonfinite price in risk lookback")
    if (numeric <= 0).to_numpy().any():
        raise ValueError("positive prices required for risk returns")
    returns = numeric.pct_change(fill_method=None).iloc[1:]
    if not np.isfinite(returns.to_numpy()).all():
        raise ValueError("nonfinite risk return")
    covariance = returns.cov()
    matrix = covariance.to_numpy()
    vector = w.to_numpy()
    variance = float(vector @ matrix @ vector)
    if variance < -1e-12:
        raise ValueError("covariance yields negative portfolio variance")
    daily_vol = math.sqrt(max(variance, 0.0))
    factor = math.sqrt(periods_per_year)
    if daily_vol == 0:
        component = pd.Series(0.0, index=w.index)
    else:
        component = pd.Series(vector * (matrix @ vector) / daily_vol * factor, index=w.index)
    return VirtualRiskResult(
        weights=w,
        cash_weight=1 - gross,
        total_vol_annualized=daily_vol * factor,
        component_vol_annualized=component,
        covariance_daily=covariance,
        base_currency=source.currency,
        adjustment=source.adjustment,
        mode=source.mode,
        lookback=lookback,
        periods_per_year=periods_per_year,
        start_at=window.index[0],
        end_at=window.index[-1],
        quality_reasons={asset: source.quality_reasons.get(asset, ()) for asset in w.index},
    )
