"""Strict retrospective comparison of a dated basket with a saved index series."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from market_research.contracts import PriceBar

from .baskets import BasketDefinition, basket_series, compare_basket
from .dataset import PriceDataset


@dataclass(frozen=True, slots=True)
class OfficialIndexComparison:
    basket_definition: BasketDefinition
    index_name: str
    index_instrument_id: str
    index_source_ref: str
    values: pd.DataFrame
    as_of: datetime
    currency: str
    adjustment: str
    session_dates: tuple[date, ...]
    bar_ends: tuple[datetime, ...]
    basket_snapshot_ids: tuple[str, ...]
    index_snapshot_ids: tuple[str, ...]
    snapshot_observed_at: tuple[tuple[str, datetime], ...]
    assumptions: tuple[str, ...]
    mode: str = "retrospective"


def _check_snapshots(
    basket_prices: PriceDataset,
    index_prices: PriceDataset,
    observed_at: Mapping[str, datetime],
) -> tuple[tuple[str, datetime], ...]:
    basket_ids = basket_prices.snapshot_ids
    index_ids = index_prices.snapshot_ids
    all_ids = (*basket_ids, *index_ids)
    if (
        not all_ids
        or not basket_ids
        or not index_ids
        or len(all_ids) != len(set(all_ids))
        or not isinstance(observed_at, Mapping)
        or set(observed_at) != set(all_ids)
    ):
        raise ValueError("snapshot IDs and observed times must match exactly")
    observations = tuple((snapshot_id, observed_at[snapshot_id]) for snapshot_id in all_ids)
    for snapshot_id, time in observations:
        if not isinstance(time, datetime) or time.utcoffset() is None:
            raise ValueError(f"snapshot observation time must be timezone-aware: {snapshot_id}")
        if time > basket_prices.as_of:
            raise ValueError(f"future snapshot cannot be compared: {snapshot_id}")
    return observations


def _complete_daily_closes(
    dataset: PriceDataset,
    expected_assets: tuple[str, ...],
    *,
    label: str,
) -> tuple[tuple[date, ...], tuple[datetime, ...]]:
    if dataset.gaps:
        raise ValueError(f"{label} contains a price gap")
    if dataset.exclusions:
        raise ValueError(f"{label} contains a price exclusion")
    if not dataset.bars:
        raise ValueError(f"{label} has no saved price bars")
    expected = set(expected_assets)
    by_asset: dict[str, dict[date, PriceBar]] = {asset: {} for asset in expected_assets}
    providers: dict[str, str] = {}
    for bar in dataset.bars:
        asset = bar.instrument.instrument_id
        if asset not in expected:
            raise ValueError(f"{label} contains an unexpected instrument: {asset}")
        if bar.interval != "1d" or not bar.is_final:
            raise ValueError(f"{label} requires final daily price bars")
        if bar.instrument.currency != dataset.currency:
            raise ValueError(f"{label} bar currency mismatch")
        if bar.adjustment != dataset.adjustment:
            raise ValueError(f"{label} bar adjustment mismatch")
        if bar.available_at > dataset.as_of or bar.observed_at > dataset.as_of:
            raise ValueError(f"future price bar in {label}")
        if bar.quality != "ok":
            raise ValueError(f"{label} contains a non-ok price bar")
        previous_provider = providers.setdefault(asset, bar.provider)
        if previous_provider != bar.provider:
            raise ValueError(f"{label} provider mixing for {asset}")
        if bar.session_date in by_asset[asset]:
            raise ValueError(f"{label} contains duplicate session prices for {asset}")
        by_asset[asset][bar.session_date] = bar
    dates = set(by_asset[expected_assets[0]])
    if not dates or any(set(bars) != dates for bars in by_asset.values()):
        raise ValueError(f"{label} has a missing constituent session")
    ordered = tuple(sorted(dates))
    ends: list[datetime] = []
    for session in ordered:
        same_session = {bars[session].bar_end for bars in by_asset.values()}
        if len(same_session) != 1:
            raise ValueError(f"{label} bar end differs within a session")
        ends.append(same_session.pop())
    return ordered, tuple(ends)


def compare_official_index(
    basket_prices: PriceDataset,
    definition: BasketDefinition,
    index_prices: PriceDataset,
    *,
    index_name: str,
    index_instrument_id: str,
    index_source_ref: str,
    snapshot_observed_at: Mapping[str, datetime],
) -> OfficialIndexComparison:
    """Compare matching saved closes, with the official source attested by the caller.

    The snapshot times should come from ResearchStore.get_snapshot for each selected
    ID. The result is retrospective: present-day basket composition is applied to
    earlier prices, and no historical index membership or PIT result is inferred.
    """
    if not isinstance(definition, BasketDefinition):
        raise ValueError("a dated basket composition is required")
    if not isinstance(index_name, str) or not index_name.strip():
        raise ValueError("index name is required")
    if not isinstance(index_instrument_id, str) or not index_instrument_id.strip():
        raise ValueError("index instrument ID is required")
    if not isinstance(index_source_ref, str) or not index_source_ref.strip():
        raise ValueError("index source reference is required")
    if index_instrument_id in definition.constituents:
        raise ValueError("index instrument cannot be a basket constituent")
    if basket_prices.mode != "retrospective" or index_prices.mode != "retrospective":
        raise ValueError("official index comparison requires retrospective price datasets")
    if (
        not isinstance(basket_prices.as_of, datetime)
        or basket_prices.as_of.utcoffset() is None
        or not isinstance(index_prices.as_of, datetime)
        or index_prices.as_of.utcoffset() is None
        or basket_prices.as_of != index_prices.as_of
    ):
        raise ValueError("basket and index as_of must match and be timezone-aware")
    if definition.composition_as_of > basket_prices.as_of.date():
        raise ValueError("composition date cannot follow the selected snapshot")
    if (
        definition.factors_as_of is not None
        and definition.factors_as_of > basket_prices.as_of.date()
    ):
        raise ValueError("factors date cannot follow the selected snapshot")
    if basket_prices.currency != index_prices.currency:
        raise ValueError("basket and index currency must match")
    if basket_prices.adjustment != index_prices.adjustment:
        raise ValueError("basket and index adjustment must match")
    if basket_prices.adjustment not in {"raw", "split", "total_return"}:
        raise ValueError("a known adjustment is required for index comparison")
    observations = _check_snapshots(basket_prices, index_prices, snapshot_observed_at)
    dates, ends = _complete_daily_closes(basket_prices, definition.constituents, label="basket")
    index_dates, index_ends = _complete_daily_closes(
        index_prices, (index_instrument_id,), label="index"
    )
    if dates != index_dates:
        raise ValueError("basket and index session dates must match")
    if ends != index_ends:
        raise ValueError("basket and index bar end times must match")
    basket = basket_series(basket_prices, definition)
    compared = compare_basket(basket, index_prices, benchmark_name=index_name)
    values = compared.values.rename(columns={"benchmark_level": "official_index_level"})
    if values.isna().any().any():
        raise ValueError("basket and index comparison contains missing values")
    return OfficialIndexComparison(
        basket_definition=definition,
        index_name=index_name,
        index_instrument_id=index_instrument_id,
        index_source_ref=index_source_ref,
        values=values,
        as_of=basket_prices.as_of,
        currency=basket_prices.currency,
        adjustment=basket_prices.adjustment,
        session_dates=dates,
        bar_ends=ends,
        basket_snapshot_ids=basket_prices.snapshot_ids,
        index_snapshot_ids=index_prices.snapshot_ids,
        snapshot_observed_at=observations,
        assumptions=(
            *basket.assumptions,
            "official_index_source_declared_by_caller",
            "not_point_in_time",
        ),
    )
