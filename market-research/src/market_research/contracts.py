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
        if not isinstance(self.is_final, bool):
            raise ValueError("is_final must be a bool")
        if self.is_final and self.available_at < self.bar_end:
            raise ValueError("available_at must be at or after bar_end for a final bar")
        if not self.is_final and min(self.available_at, self.observed_at) < self.bar_start:
            raise ValueError("partial bar cannot be observed before bar_start")
        if not math.isfinite(self.close) or self.close <= 0:
            raise ValueError("close must be positive and finite")
        if self.adjustment not in ADJUSTMENTS:
            raise ValueError(f"invalid adjustment: {self.adjustment}")
        if self.quality not in QUALITY_STATES:
            raise ValueError(f"invalid quality: {self.quality}")
        object.__setattr__(
            self,
            "session_date",
            (
                self.bar_start
                if self.instrument.market == "CRYPTO" and self.interval == "1d"
                else self.bar_end
            )
            .astimezone(ZoneInfo(self.instrument.timezone))
            .date(),
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
class PriceGap:
    """An observed source row without a traded price; never an imputed PriceBar."""

    instrument: Instrument
    provider: str
    provider_symbol: str
    interval: str
    session_date: date
    available_at: datetime
    observed_at: datetime
    adjustment: str
    reason: str = "no_trade"

    def __post_init__(self):
        for name in ("provider", "provider_symbol", "interval", "reason"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        for name in ("available_at", "observed_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if type(self.session_date) is not date or self.adjustment not in ADJUSTMENTS:
            raise ValueError("invalid gap session date or adjustment")


@dataclass(frozen=True, slots=True)
class MacroObservation:
    indicator: str
    period_start: date
    release_at: datetime
    value: float
    source: str
    vintage_id: str
    vintage_kind: str = "actual"
    unit: str | None = None
    frequency: str | None = None
    seasonal_adjustment: str | None = None
    release_precision: str = "instant"
    source_release_date: date | None = None
    observed_at: datetime | None = None
    raw_hash: str | None = None
    source_ref: str | None = None

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
        if self.release_precision not in {"instant", "date", "snapshot"}:
            raise ValueError("invalid release precision")
        if self.source_release_date is not None and type(self.source_release_date) is not date:
            raise ValueError("source_release_date must be a date")
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        if self.raw_hash is not None and (
            len(self.raw_hash) != 64 or any(c not in "0123456789abcdef" for c in self.raw_hash)
        ):
            raise ValueError("invalid raw hash")


@dataclass(frozen=True, slots=True)
class FundamentalObservation:
    cik: int
    taxonomy: str
    concept: str
    unit: str
    period_start: date | None
    period_end: date
    filed: date
    available_at: datetime
    observed_at: datetime | None
    value: float
    form: str
    accession: str
    source: str = "sec"
    vintage_kind: str = "estimated"
    raw_hash: str | None = None

    def __post_init__(self) -> None:
        if type(self.cik) is not int or self.cik <= 0:
            raise ValueError("cik must be a positive integer")
        for name in ("taxonomy", "concept", "unit", "form", "accession", "source"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if type(self.period_end) is not date or type(self.filed) is not date:
            raise ValueError("period_end and filed must be dates")
        if self.period_start is not None and (
            type(self.period_start) is not date or self.period_start > self.period_end
        ):
            raise ValueError("invalid period_start")
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        if self.observed_at is not None and self.available_at > self.observed_at:
            raise ValueError("fundamental cannot be available after observation")
        if not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.vintage_kind not in VINTAGE_KINDS:
            raise ValueError("invalid vintage kind")
        if self.raw_hash is not None and (
            len(self.raw_hash) != 64 or any(c not in "0123456789abcdef" for c in self.raw_hash)
        ):
            raise ValueError("invalid raw hash")
