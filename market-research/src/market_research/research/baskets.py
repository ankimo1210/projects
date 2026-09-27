"""Retrospective basket approximations with explicit composition assumptions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

import pandas as pd

from .dataset import PriceDataset
from .indicators import close_history


@dataclass(frozen=True, slots=True)
class BasketDefinition:
    name: str
    constituents: tuple[str, ...]
    composition_as_of: date
    source_ref: str
    weighting: str
    factors: Mapping[str, float] | None = None
    factors_as_of: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("basket name is required")
        if not isinstance(self.source_ref, str) or not self.source_ref.strip():
            raise ValueError("basket composition source is required")
        if not self.constituents or len(self.constituents) != len(set(self.constituents)):
            raise ValueError("basket constituents must be nonempty and unique")
        if type(self.composition_as_of) is not date:
            raise ValueError("composition date is required")
        if self.weighting not in {"price", "market_cap"}:
            raise ValueError("basket weighting must be price or market_cap")
        if self.factors is None:
            if self.weighting == "market_cap":
                raise ValueError("market-cap factors and their date are required")
            if self.factors_as_of is None:
                object.__setattr__(self, "factors_as_of", self.composition_as_of)
            elif type(self.factors_as_of) is not date:
                raise ValueError("PAF assumption date is required")
        else:
            factors = dict(self.factors)
            if set(factors) != set(self.constituents):
                raise ValueError("factors must cover exactly the basket constituents")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
                for value in factors.values()
            ):
                raise ValueError("factors must be positive finite values")
            if type(self.factors_as_of) is not date:
                raise ValueError("factors date is required")
            object.__setattr__(self, "factors", MappingProxyType(factors))


@dataclass(frozen=True, slots=True)
class BasketResult:
    definition: BasketDefinition
    values: pd.DataFrame
    weights: pd.DataFrame
    currency: str
    adjustment: str
    as_of: datetime
    session_dates: tuple[date, ...]
    snapshot_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    quality_reasons: Mapping[str, tuple[str, ...]]
    mode: str = "retrospective"


def basket_series(dataset: PriceDataset, definition: BasketDefinition) -> BasketResult:
    """Apply a dated present-day composition to a display history, never to PIT weights."""
    if dataset.mode != "retrospective":
        raise ValueError("basket approximation requires retrospective price history")
    if definition.composition_as_of > dataset.as_of.date():
        raise ValueError("composition date cannot follow the price snapshot")
    if definition.factors_as_of is not None and definition.factors_as_of > dataset.as_of.date():
        raise ValueError("factors date cannot follow the price snapshot")
    selected = set(definition.constituents)
    for bar in dataset.bars:
        if bar.instrument.instrument_id not in selected:
            continue
        if bar.interval != "1d":
            raise ValueError("basket requires daily price bars")
        if bar.instrument.currency != dataset.currency:
            raise ValueError("basket currency mismatch")
        if bar.adjustment != dataset.adjustment:
            raise ValueError("basket adjustment mismatch")
    for gap in dataset.gaps:
        if gap.instrument.instrument_id in selected and gap.interval != "1d":
            raise ValueError("basket requires daily price gaps")
    for exclusion in dataset.exclusions:
        if exclusion.bar.instrument.instrument_id in selected and exclusion.bar.interval != "1d":
            raise ValueError("basket requires daily excluded bars")

    history = close_history(dataset)
    if not selected.issubset(history.prices.columns):
        raise ValueError("basket constituent prices are missing")
    prices = history.prices.reindex(columns=definition.constituents).astype(float)
    if definition.factors is None:
        factors = pd.Series(1.0, index=definition.constituents)
        factor_assumption = "PAF_assumed_1"
    else:
        factors = pd.Series(definition.factors, dtype=float).reindex(definition.constituents)
        factor_assumption = "fixed_PAF" if definition.weighting == "price" else "fixed_shares"
    weighted = prices.mul(factors, axis=1)
    total = weighted.sum(axis=1, min_count=len(definition.constituents))
    valid = total.dropna()
    if valid.empty or valid.iloc[0] <= 0:
        raise ValueError("basket has no complete positive starting row")
    level = total / valid.iloc[0]
    values = pd.DataFrame({"level": level, "total_return": level - 1})
    weights = weighted.div(total, axis=0)
    return BasketResult(
        definition=definition,
        values=values,
        weights=weights,
        currency=dataset.currency,
        adjustment=dataset.adjustment,
        as_of=dataset.as_of,
        session_dates=history.session_dates,
        snapshot_ids=dataset.snapshot_ids,
        assumptions=("current_composition_applied_historically", factor_assumption),
        quality_reasons={
            asset: history.quality_reasons.get(asset, ()) for asset in definition.constituents
        },
    )


@dataclass(frozen=True, slots=True)
class BasketComparison:
    benchmark_name: str
    values: pd.DataFrame
    currency: str
    adjustment: str
    snapshot_ids: tuple[str, ...]
    mode: str = "retrospective"


def compare_basket(
    basket: BasketResult, benchmark: PriceDataset, *, benchmark_name: str
) -> BasketComparison:
    """Compare only matching dated daily closes, without filling either side."""
    if not isinstance(benchmark_name, str) or not benchmark_name.strip():
        raise ValueError("benchmark name is required")
    if basket.mode != "retrospective" or benchmark.mode != "retrospective":
        raise ValueError("benchmark comparison requires retrospective inputs")
    if basket.as_of != benchmark.as_of:
        raise ValueError("basket and benchmark as_of must match")
    if basket.currency != benchmark.currency:
        raise ValueError("basket and benchmark currency must match")
    if basket.adjustment != benchmark.adjustment:
        raise ValueError("basket and benchmark adjustment must match")
    history = close_history(benchmark)
    if len(history.prices.columns) != 1:
        raise ValueError("benchmark must contain exactly one instrument")
    if history.session_dates != basket.session_dates:
        raise ValueError("basket and benchmark session dates must match")
    reference = history.prices.iloc[:, 0].astype(float)
    basket_level = basket.values["level"]
    if any(
        left != right
        for left, right, left_price, right_price in zip(
            basket_level.index,
            reference.index,
            basket_level,
            reference,
            strict=True,
        )
        if pd.notna(left_price) and pd.notna(right_price)
    ):
        raise ValueError("basket and benchmark close timestamps must match")
    valid = basket_level.notna().to_numpy() & reference.notna().to_numpy()
    if not valid.any():
        raise ValueError("basket and benchmark have no common complete row")
    first = int(valid.argmax())
    basket_relative = basket_level / basket_level.iloc[first]
    benchmark_relative = reference.to_numpy() / reference.iloc[first]
    values = pd.DataFrame(
        {
            "basket_level": basket_relative.to_numpy(),
            "benchmark_level": benchmark_relative,
        },
        index=basket_level.index,
    )
    values.iloc[:first] = float("nan")
    values["relative_return"] = values["basket_level"] / values["benchmark_level"] - 1
    return BasketComparison(
        benchmark_name=benchmark_name,
        values=values,
        currency=basket.currency,
        adjustment=basket.adjustment,
        snapshot_ids=(*basket.snapshot_ids, *benchmark.snapshot_ids),
    )
