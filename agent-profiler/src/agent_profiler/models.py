"""Provider-independent event and metric models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Category = Literal[
    "model_wait",
    "reasoning",
    "search",
    "read",
    "edit",
    "shell",
    "test",
    "web",
    "subagent",
    "user_wait",
    "other",
]
Measurement = Literal["actual", "reconciled", "estimated", "unknown"]
TimestampSource = Literal["provider", "received"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_timestamp(value: object, fallback: datetime) -> tuple[datetime, TimestampSource]:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC), "provider"
        except ValueError:
            pass
    return fallback.astimezone(UTC), "received"


@dataclass(slots=True)
class TokenUsage:
    """Token counts reported by a provider or a reconciliation source.

    Reasoning output is a subset of output for both currently supported
    providers, so it is not added a second time when deriving total tokens.
    """

    actual_input_tokens: int | None = None
    actual_cached_input_tokens: int | None = None
    actual_cache_write_input_tokens: int | None = None
    actual_output_tokens: int | None = None
    actual_reasoning_tokens: int | None = None
    actual_total_tokens: int | None = None
    source: Measurement = "actual"

    def __post_init__(self) -> None:
        values = (
            self.actual_input_tokens,
            self.actual_cached_input_tokens,
            self.actual_cache_write_input_tokens,
            self.actual_output_tokens,
            self.actual_reasoning_tokens,
            self.actual_total_tokens,
        )
        if any(value is not None and value < 0 for value in values):
            raise ValueError("token counts must be non-negative")
        if self.actual_total_tokens is None:
            parts = (
                self.actual_input_tokens,
                self.actual_cached_input_tokens,
                self.actual_output_tokens,
            )
            if any(value is not None for value in parts):
                self.actual_total_tokens = sum(value or 0 for value in parts)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NormalizedEvent:
    """Stable schema consumed by metrics, storage, reports, and the TUI."""

    timestamp: datetime
    provider: str
    event_type: str
    category: Category = "other"
    status: str | None = None
    session_id: str | None = None
    event_id: str | None = None
    correlation_id: str | None = None
    tool_name: str | None = None
    command: str | None = None
    file_path: str | None = None
    duration_ms: int | None = None
    usage: TokenUsage | None = None
    output_bytes: int | None = None
    parent_agent_id: str | None = None
    agent_id: str | None = None
    raw_event_type: str = "unknown"
    timestamp_source: TimestampSource = "received"
    measurement: Measurement = "actual"
    schema_version: int = 1
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)
        else:
            self.timestamp = self.timestamp.astimezone(UTC)
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        if self.output_bytes is not None and self.output_bytes < 0:
            raise ValueError("output_bytes must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat().replace("+00:00", "Z")
        if self.usage is not None:
            data["usage"] = self.usage.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizedEvent:
        value = dict(data)
        timestamp, source = parse_timestamp(value.pop("timestamp", None), utc_now())
        usage_data = value.get("usage")
        if isinstance(usage_data, dict):
            value["usage"] = TokenUsage(**usage_data)
        value.setdefault("timestamp_source", source)
        return cls(timestamp=timestamp, **value)


@dataclass(slots=True)
class Span:
    correlation_id: str
    category: Category
    started_at: datetime
    ended_at: datetime
    label: str
    measurement: Measurement
    agent_id: str | None = None
    incomplete: bool = False

    @property
    def duration_ms(self) -> int:
        return max(0, round((self.ended_at - self.started_at).total_seconds() * 1000))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat().replace("+00:00", "Z")
        data["ended_at"] = self.ended_at.isoformat().replace("+00:00", "Z")
        data["duration_ms"] = self.duration_ms
        return data
