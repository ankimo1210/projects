"""Immutable identifiers and timestamps shared by research inputs."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ADJUSTMENTS = frozenset({"raw", "split", "total_return", "unknown"})
QUALITY_STATES = frozenset({"ok", "warn", "reject"})
VINTAGE_KINDS = frozenset({"actual", "snapshot", "estimated"})


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Instrument:
    market: str
    symbol: str
    currency: str
    timezone: str

    def __post_init__(self) -> None:
        for name in ("market", "symbol", "currency", "timezone"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"invalid timezone: {self.timezone}") from exc
        object.__setattr__(self, "market", self.market.strip().upper())
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "currency", self.currency.strip().upper())

    @property
    def instrument_id(self) -> str:
        return f"{self.market}:{self.symbol}"


@dataclass(frozen=True, slots=True)
class PriceBar:
    instrument: Instrument
    provider: str
    interval: str
    bar_start: datetime
    bar_end: datetime
    available_at: datetime
    observed_at: datetime
    close: float
    adjustment: str
    revision_id: str
    quality: str = "ok"
    quality_reasons: tuple[str, ...] = ()
    provider_symbol: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    volume_unit: str | None = None
    supersedes: str | None = None
    is_final: bool = True
    session_date: date = field(init=False)

    def __post_init__(self) -> None:
        for name in ("provider", "interval", "revision_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty")
        for name in ("bar_start", "bar_end", "available_at", "observed_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.bar_start >= self.bar_end:
            raise ValueError("bar_start must precede bar_end")
        if self.available_at < self.bar_end:
            raise ValueError("available_at must be at or after bar_end")
        if not math.isfinite(self.close) or self.close <= 0:
            raise ValueError("close must be positive and finite")
        if self.adjustment not in ADJUSTMENTS:
            raise ValueError(f"invalid adjustment: {self.adjustment}")
        if self.quality not in QUALITY_STATES:
            raise ValueError(f"invalid quality: {self.quality}")
        object.__setattr__(
            self, "session_date", self.bar_end.astimezone(ZoneInfo(self.instrument.timezone)).date()
        )

    @property
    def key(self) -> tuple[str, str, str, datetime, str, str]:
        return (
            self.instrument.instrument_id,
            self.provider,
            self.interval,
            self.bar_end,
            self.adjustment,
            self.revision_id,
        )


@dataclass(frozen=True, slots=True)
class MacroObservation:
    indicator: str
    period_start: date
    release_at: datetime
    value: float
    source: str
    vintage_id: str
    vintage_kind: str = "actual"

    def __post_init__(self) -> None:
        for name in ("indicator", "source", "vintage_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty")
        if not isinstance(self.period_start, date):
            raise ValueError("period_start must be a date")
        object.__setattr__(self, "release_at", _utc(self.release_at, "release_at"))
        if not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.vintage_kind not in VINTAGE_KINDS:
            raise ValueError("vintage_kind must be actual, snapshot, or estimated")
