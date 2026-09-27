"""Conservative price normalization and point-in-time revision selection."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pandas as pd

from .contracts import Instrument, PriceBar


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class BarTiming:
    """Caller-verified session bounds and finality for one provider row."""

    bar_start: datetime
    bar_end: datetime
    is_final: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "bar_start", _aware_utc(self.bar_start, "bar_start"))
        object.__setattr__(self, "bar_end", _aware_utc(self.bar_end, "bar_end"))
        if self.bar_start >= self.bar_end:
            raise ValueError("bar_start must precede bar_end")
        if not isinstance(self.is_final, bool):
            raise ValueError("is_final must be a bool")


def _single_symbol_columns(raw: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    if not isinstance(raw.columns, pd.MultiIndex):
        return raw, None
    if raw.columns.nlevels != 2:
        raise ValueError("expected two yfinance column levels")
    first = set(raw.columns.get_level_values(0))
    second = set(raw.columns.get_level_values(1))
    if "Close" in first:
        symbols = second
        symbol_level = 1
    elif "Close" in second:
        symbols = first
        symbol_level = 0
    else:
        raise ValueError("missing Close column")
    if len(symbols) != 1:
        raise ValueError("one instrument per price batch is required")
    symbol = next(iter(symbols))
    frame = raw.xs(symbol, axis=1, level=symbol_level, drop_level=True)
    return frame, str(symbol)


def normalize_yfinance(
    raw: pd.DataFrame,
    instrument: Instrument,
    observed_at: datetime,
    *,
    expected_provider_symbol: str | None = None,
    bar_timing: Mapping[pd.Timestamp, BarTiming] | None = None,
) -> tuple[PriceBar, ...]:
    """Read a one-symbol snapshot using explicit provider identity and bar timing.

    yfinance's daily index may be a session-date label, not a bar end. The
    caller must resolve every label against a verified calendar/provider
    interval. Snapshot rows become available no earlier than observation.
    ``Adj Close`` remains an unclassified adjustment until verified.
    """
    observed = _aware_utc(observed_at, "observed_at")
    if raw.empty:
        raise ValueError("empty price response")
    frame, input_symbol = _single_symbol_columns(raw)
    if "Close" not in frame.columns:
        raise ValueError("missing Close column")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError("price index must be timezone-aware session labels")
    if frame.index.has_duplicates:
        raise ValueError("duplicate session labels")
    if not isinstance(expected_provider_symbol, str) or not expected_provider_symbol.strip():
        raise ValueError("expected_provider_symbol is required")
    provider_symbol = expected_provider_symbol.strip()
    if input_symbol is not None and input_symbol.upper() != provider_symbol.upper():
        raise ValueError(f"provider symbol mismatch: {input_symbol} != {provider_symbol}")
    if bar_timing is None or set(bar_timing) != set(frame.index):
        raise ValueError("bar_timing must contain verified bounds for every source row")
    result: list[PriceBar] = []
    for index, row in frame.sort_index().iterrows():
        timing = bar_timing[index]
        if not isinstance(timing, BarTiming):
            raise ValueError(f"bar_timing must use BarTiming for {index}")
        fields = {
            "open": float(row["Open"]) if "Open" in frame and pd.notna(row["Open"]) else None,
            "high": float(row["High"]) if "High" in frame and pd.notna(row["High"]) else None,
            "low": float(row["Low"]) if "Low" in frame and pd.notna(row["Low"]) else None,
            "volume": float(row["Volume"])
            if "Volume" in frame and pd.notna(row["Volume"])
            else None,
        }
        common = dict(
            instrument=instrument,
            provider="yfinance",
            provider_symbol=input_symbol or provider_symbol,
            interval="1d",
            bar_start=timing.bar_start,
            bar_end=timing.bar_end,
            available_at=observed,
            observed_at=observed,
            revision_id=f"yf:{observed.isoformat()}",
            is_final=timing.is_final,
            volume_unit="shares",
            **fields,
        )
        result.append(PriceBar(close=float(row["Close"]), adjustment="raw", **common))
        if "Adj Close" in frame.columns and pd.notna(row["Adj Close"]):
            result.append(
                PriceBar(
                    close=float(row["Adj Close"]),
                    adjustment="unknown",
                    **{**common, "open": None, "high": None, "low": None},
                )
            )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class PriceExclusion:
    bar: PriceBar
    reason: str


@dataclass(frozen=True, slots=True)
class PriceView:
    bars: tuple[PriceBar, ...]
    exclusions: tuple[PriceExclusion, ...]


def price_view_as_of(
    bars: Iterable[PriceBar], decision_at: datetime, *, adjustment: str | None = None
) -> PriceView:
    """Select final revisions and retain an audit of excluded unfinished observations."""
    when = _aware_utc(decision_at, "decision_at")
    seen: set[tuple[str, str, str, datetime, str, str]] = set()
    latest: dict[tuple[str, str, str, datetime, str], PriceBar] = {}
    exclusions: list[PriceExclusion] = []
    for bar in bars:
        if bar.available_at > when:
            continue
        if adjustment is not None and bar.adjustment != adjustment:
            continue
        if not bar.is_final:
            exclusions.append(PriceExclusion(bar, "non_final"))
            continue
        if bar.key in seen:
            raise ValueError(f"duplicate price revision: {bar.key}")
        seen.add(bar.key)
        base_key = bar.key[:-1]
        previous = latest.get(base_key)
        if previous is None or bar.available_at > previous.available_at:
            latest[base_key] = bar
        elif bar.available_at == previous.available_at:
            raise ValueError(f"conflicting price revisions: {base_key}")
    if adjustment is not None and not latest and not exclusions:
        raise ValueError(f"requested adjustment unavailable: {adjustment}")
    selected = tuple(
        sorted(
            latest.values(),
            key=lambda b: (
                b.instrument.instrument_id,
                b.provider,
                b.interval,
                b.adjustment,
                b.bar_end,
            ),
        )
    )

    return PriceView(selected, tuple(exclusions))


def select_bars_as_of(
    bars: Iterable[PriceBar], decision_at: datetime, *, adjustment: str | None = None
) -> tuple[PriceBar, ...]:
    """Compatibility reader; use price_view_as_of for row-level exclusion details."""
    view = price_view_as_of(bars, decision_at, adjustment=adjustment)
    if view.exclusions:
        logging.getLogger(__name__).warning(
            "Excluded %d non_final price observations", len(view.exclusions)
        )
    return view.bars


def assess_bars(bars: Iterable[PriceBar], as_of: datetime) -> tuple[PriceBar, ...]:
    """Flag large moves using only rows knowable by ``as_of``; never rewrite prices."""
    selected = select_bars_as_of(bars, as_of)
    groups: dict[tuple[str, str, str, str], list[PriceBar]] = defaultdict(list)
    for bar in selected:
        groups[(bar.instrument.instrument_id, bar.provider, bar.interval, bar.adjustment)].append(
            bar
        )
    result: list[PriceBar] = []
    for group in groups.values():
        previous: PriceBar | None = None
        for bar in sorted(group, key=lambda item: item.bar_end):
            if previous is not None and not 0.25 <= bar.close / previous.close <= 4.0:
                reasons = tuple(dict.fromkeys((*bar.quality_reasons, "large_close_jump")))
                state = "reject" if bar.quality == "reject" else "warn"
                bar = replace(bar, quality=state, quality_reasons=reasons)
            result.append(bar)
            previous = bar
    return tuple(
        sorted(
            result,
            key=lambda b: (
                b.instrument.instrument_id,
                b.provider,
                b.interval,
                b.adjustment,
                b.bar_end,
            ),
        )
    )
