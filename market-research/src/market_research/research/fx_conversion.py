"""Strict, retrospective conversion of saved daily USD closes into JPY."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

import pandas as pd

from market_research.contracts import PriceBar

from .dataset import PriceDataset
from .indicators import IndicatorInput


@dataclass(frozen=True, slots=True)
class FxUse:
    session_date: date
    valuation_at: datetime
    rate: float
    snapshot_id: str
    instrument_id: str
    provider: str
    provider_symbol: str
    bar_end: datetime
    available_at: datetime
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class FxConversionResult:
    source: IndicatorInput
    fx_uses: tuple[FxUse, ...]
    price_snapshot_ids: tuple[str, ...]
    fx_snapshot_id: str
    as_of: datetime
    assumption: str = "retrospective_non_pit"


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _check_bar(bar: PriceBar, *, as_of: datetime, currency: str) -> None:
    if bar.instrument.currency != currency:
        raise ValueError("bar currency differs from dataset currency")
    if bar.interval != "1d" or bar.adjustment != "raw":
        raise ValueError("raw daily price bars are required")
    if not bar.is_final:
        raise ValueError("non_final price bar cannot be converted")
    if bar.quality != "ok":
        raise ValueError("price quality must be ok")
    if bar.available_at > as_of or bar.observed_at > as_of:
        raise ValueError("future observation relative to dataset as_of")


def convert_price_datasets_to_jpy(
    datasets: Sequence[PriceDataset],
    fx_dataset: PriceDataset,
    valuation_times: Mapping[date, datetime],
    *,
    max_fx_age: timedelta,
) -> FxConversionResult:
    """Convert complete saved raw daily bars at explicit historical evaluation times.

    A final bar can become available after its ``bar_end``. Therefore callers
    provide each evaluation time, and both price and FX observations must have
    existed by that time. Bulk downloads made later are rejected for earlier
    evaluations. The result remains retrospective, not a PIT backtest: its
    snapshot and instrument selection was made after the fact.
    """
    if not datasets:
        raise ValueError("at least one price dataset is required")
    if not isinstance(max_fx_age, timedelta) or max_fx_age < timedelta(0):
        raise ValueError("max_fx_age must be a nonnegative timedelta")
    as_of = _aware_utc(datasets[0].as_of, "as_of")
    if _aware_utc(fx_dataset.as_of, "FX as_of") != as_of:
        raise ValueError("price and FX datasets must share as_of")
    if not valuation_times:
        raise ValueError("valuation_times must be nonempty")
    times = {}
    for day, when in valuation_times.items():
        if type(day) is not date:
            raise ValueError("valuation_times keys must be session dates")
        at = _aware_utc(when, "valuation_at")
        if at > as_of:
            raise ValueError("valuation_at is after as_of")
        times[day] = at
    days = sorted(times)
    if any(times[left] >= times[right] for left, right in pairwise(days)):
        raise ValueError("valuation_times must increase with session dates")

    prices: dict[tuple[date, str], PriceBar] = {}
    assets: dict[str, str] = {}
    providers: dict[str, str] = {}
    price_snapshot_ids: list[str] = []
    quality_reasons: dict[str, tuple[str, ...]] = {}
    for dataset in datasets:
        if _aware_utc(dataset.as_of, "price as_of") != as_of:
            raise ValueError("price datasets must share as_of")
        if dataset.mode != "retrospective" or dataset.adjustment != "raw":
            raise ValueError("retrospective raw price datasets are required")
        if dataset.currency not in {"USD", "JPY"}:
            raise ValueError("only USD and JPY prices can be converted")
        if not dataset.snapshot_ids:
            raise ValueError("saved price snapshot IDs are required")
        price_snapshot_ids.extend(dataset.snapshot_ids)
        for bar in dataset.bars:
            _check_bar(bar, as_of=as_of, currency=dataset.currency)
            asset = bar.instrument.instrument_id
            if asset in assets and assets[asset] != dataset.currency:
                raise ValueError("asset currency is inconsistent")
            assets[asset] = dataset.currency
            if asset in providers and providers[asset] != bar.provider:
                raise ValueError("asset provider switched across saved prices")
            providers[asset] = bar.provider
            key = (bar.session_date, asset)
            if key in prices:
                raise ValueError("duplicate daily price")
            prices[key] = bar
            quality_reasons[asset] = tuple(bar.quality_reasons)
        for gap in dataset.gaps:
            if gap.available_at > as_of or gap.observed_at > as_of:
                raise ValueError("future price gap relative to as_of")
            if days[0] <= gap.session_date <= days[-1]:
                raise ValueError(f"price gap on {gap.session_date}")
        for exclusion in dataset.exclusions:
            bar = exclusion.bar
            if bar.available_at > as_of or bar.observed_at > as_of:
                raise ValueError("future excluded price relative to as_of")
            if days[0] <= bar.session_date <= days[-1]:
                raise ValueError(f"price non_final on {bar.session_date}")
    if not assets:
        raise ValueError("saved price bars are missing")
    if len(price_snapshot_ids) != len(set(price_snapshot_ids)):
        raise ValueError("duplicate price snapshot ID")
    if set(days) != {day for day, _ in prices}:
        raise ValueError("valuation dates must match saved price session dates")

    if fx_dataset.mode != "retrospective" or fx_dataset.adjustment != "raw":
        raise ValueError("retrospective raw FX dataset is required")
    if fx_dataset.currency != "JPY" or len(fx_dataset.snapshot_ids) != 1:
        raise ValueError("one saved JPY FX snapshot is required")
    fx_bars = []
    fx_identity = None
    fx_ends = set()
    for bar in fx_dataset.bars:
        _check_bar(bar, as_of=as_of, currency="JPY")
        if bar.provider_symbol != "JPY=X":
            raise ValueError("JPY=X FX provider_symbol is required")
        if bar.instrument.instrument_id != "FX:JPY=X":
            raise ValueError("FX instrument must be FX:JPY=X")
        identity = (bar.instrument.instrument_id, bar.provider)
        if fx_identity is not None and fx_identity != identity:
            raise ValueError("FX instrument or provider mixing")
        fx_identity = identity
        if bar.bar_end in fx_ends:
            raise ValueError("duplicate FX close")
        fx_ends.add(bar.bar_end)
        fx_bars.append(bar)
    if not fx_bars:
        raise ValueError("FX prices are missing")
    for gap in fx_dataset.gaps:
        if (
            gap.instrument.currency != "JPY"
            or gap.instrument.instrument_id != "FX:JPY=X"
            or gap.provider_symbol != "JPY=X"
            or gap.adjustment != "raw"
            or gap.interval != "1d"
            or gap.available_at > as_of
            or gap.observed_at > as_of
        ):
            raise ValueError("invalid FX gap")
    for exclusion in fx_dataset.exclusions:
        bar = exclusion.bar
        if (
            bar.instrument.currency != "JPY"
            or bar.instrument.instrument_id != "FX:JPY=X"
            or bar.provider_symbol != "JPY=X"
            or bar.adjustment != "raw"
            or bar.interval != "1d"
            or bar.available_at > as_of
            or bar.observed_at > as_of
        ):
            raise ValueError("invalid FX non_final bar")

    rows: list[dict[str, float]] = []
    uses: list[FxUse] = []
    for day in days:
        valuation_at = times[day]
        latest_fx = [
            bar
            for bar in fx_bars
            if bar.bar_end <= valuation_at
            and bar.available_at <= valuation_at
            and bar.observed_at <= valuation_at
        ]
        if not latest_fx:
            raise ValueError(f"FX is missing at valuation {day}")
        fx_bar = max(latest_fx, key=lambda bar: bar.bar_end)
        if any(
            fx_bar.session_date <= gap.session_date <= day
            and gap.available_at <= valuation_at
            and gap.observed_at <= valuation_at
            for gap in fx_dataset.gaps
        ):
            raise ValueError(f"FX gap at valuation {day}")
        if any(
            fx_bar.session_date <= exclusion.bar.session_date <= day
            and exclusion.bar.available_at <= valuation_at
            and exclusion.bar.observed_at <= valuation_at
            for exclusion in fx_dataset.exclusions
        ):
            raise ValueError(f"FX non_final at valuation {day}")
        if valuation_at - fx_bar.bar_end > max_fx_age:
            raise ValueError(f"FX is stale at valuation {day}")
        row: dict[str, float] = {}
        for asset, currency in assets.items():
            price = prices.get((day, asset))
            if price is None:
                raise ValueError(f"missing price for {asset} on {day}")
            if (
                price.bar_end > valuation_at
                or price.available_at > valuation_at
                or price.observed_at > valuation_at
            ):
                raise ValueError(f"price observed after valuation for {asset} on {day}")
            row[asset] = float(price.close) * (float(fx_bar.close) if currency == "USD" else 1.0)
        rows.append(row)
        uses.append(
            FxUse(
                session_date=day,
                valuation_at=valuation_at,
                rate=float(fx_bar.close),
                snapshot_id=fx_dataset.snapshot_ids[0],
                instrument_id=fx_bar.instrument.instrument_id,
                provider=fx_bar.provider,
                provider_symbol="JPY=X",
                bar_end=fx_bar.bar_end,
                available_at=fx_bar.available_at,
                observed_at=fx_bar.observed_at,
            )
        )
    frame = pd.DataFrame(rows, index=pd.DatetimeIndex([times[day] for day in days]))
    source = IndicatorInput(frame, "retrospective", "JPY", "raw", quality_reasons, {}, tuple(days))
    return FxConversionResult(
        source=source,
        fx_uses=tuple(uses),
        price_snapshot_ids=tuple(price_snapshot_ids),
        fx_snapshot_id=fx_dataset.snapshot_ids[0],
        as_of=as_of,
    )
