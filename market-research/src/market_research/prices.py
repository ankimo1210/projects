"""Conservative price normalization and point-in-time revision selection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd

from .contracts import Instrument, PriceBar


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


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
    raw: pd.DataFrame, instrument: Instrument, observed_at: datetime
) -> tuple[PriceBar, ...]:
    """Read a one-symbol snapshot; never infer publication time from a date-only index.

    The caller supplies the observed snapshot time. Historical rows become
    available no earlier than that time until source release times are known.
    An ``Adj Close`` column is retained as ``unknown`` adjustment provenance.
    """
    observed = _aware_utc(observed_at, "observed_at")
    if raw.empty:
        raise ValueError("empty price response")
    frame, provider_symbol = _single_symbol_columns(raw)
    if "Close" not in frame.columns:
        raise ValueError("missing Close column")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError("price index must be timezone-aware bar-end timestamps")
    if frame.index.has_duplicates:
        raise ValueError("duplicate bar-end timestamps")
    result: list[PriceBar] = []
    for index, row in frame.sort_index().iterrows():
        end = _aware_utc(index.to_pydatetime(), "bar_end")
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
            provider_symbol=provider_symbol or instrument.symbol,
            interval="1d",
            bar_start=end - timedelta(days=1),
            bar_end=end,
            available_at=observed,
            observed_at=observed,
            revision_id=f"yf:{observed.isoformat()}",
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


def select_bars_as_of(
    bars: Iterable[PriceBar], decision_at: datetime, *, adjustment: str | None = None
) -> tuple[PriceBar, ...]:
    """Return latest available revision per source and adjustment at a decision time."""
    when = _aware_utc(decision_at, "decision_at")
    seen: set[tuple[str, str, str, datetime, str, str]] = set()
    latest: dict[tuple[str, str, str, datetime, str], PriceBar] = {}
    for bar in bars:
        if bar.available_at > when:
            continue
        if adjustment is not None and bar.adjustment != adjustment:
            continue
        if not bar.is_final:
            raise ValueError(f"non-final bar: {bar.key}")
        if bar.key in seen:
            raise ValueError(f"duplicate price revision: {bar.key}")
        seen.add(bar.key)
        base_key = bar.key[:-1]
        previous = latest.get(base_key)
        if previous is None or bar.available_at > previous.available_at:
            latest[base_key] = bar
        elif bar.available_at == previous.available_at:
            raise ValueError(f"conflicting price revisions: {base_key}")
    if adjustment is not None and not latest:
        raise ValueError(f"requested adjustment unavailable: {adjustment}")
    return tuple(
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
