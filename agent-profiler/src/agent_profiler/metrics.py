"""Streaming metrics with ID pairing and overlap-aware time accounting."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any

from agent_profiler.classify import event_label
from agent_profiler.models import Category, NormalizedEvent, Span, TokenUsage

_FINISHED = {"completed", "failed", "cancelled", "interrupted"}


@dataclass(slots=True)
class OutputAttribution:
    label: str
    output_bytes: int
    estimated_next_turn_tokens: int
    category: Category

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "output_bytes": self.output_bytes,
            "estimated_next_turn_tokens": self.estimated_next_turn_tokens,
            "measurement": "estimated",
            "method": "ceil(UTF-8 bytes / 4)",
            "category": self.category,
        }


class MetricsEngine:
    """Incremental aggregator.

    Inclusive duration sums every span. ``exclusive_ms`` divides every
    overlapping wall-clock segment equally among the active categories, so the
    total does not double-count parallel tools.
    """

    def __init__(self, max_recent_events: int = 2_000) -> None:
        self.recent_events: deque[NormalizedEvent] = deque(maxlen=max_recent_events)
        self.open_events: dict[str, NormalizedEvent] = {}
        self.spans: list[Span] = []
        self.first_timestamp: datetime | None = None
        self.last_timestamp: datetime | None = None
        self.event_count = 0
        self.error_count = 0
        self.retry_count = 0
        self._turn_usages: list[TokenUsage] = []
        self._session_usage: TokenUsage | None = None
        self.outputs: list[OutputAttribution] = []
        self.current_status = "Starting"
        self.current_event: NormalizedEvent | None = None
        self.finalized = False

    def process(self, event: NormalizedEvent) -> None:
        if self.finalized:
            raise RuntimeError("cannot process events after finalize")
        self.event_count += 1
        self.recent_events.append(event)
        self.first_timestamp = min(
            self.first_timestamp or event.timestamp,
            event.timestamp,
        )
        self.last_timestamp = max(self.last_timestamp or event.timestamp, event.timestamp)
        countable_failures = {
            "adapter_error",
            "error",
            "oversized_event",
            "parse_error",
            "session",
            "subagent",
            "tool",
            "turn",
        }
        if event.status == "failed" and event.event_type in countable_failures:
            self.error_count += 1
        if event.event_type == "retry":
            self.retry_count += 1
        self._process_usage(event)
        self._process_output(event)
        self._process_span(event)
        self._update_status(event)

    def _process_usage(self, event: NormalizedEvent) -> None:
        if event.usage is None:
            return
        if event.details.get("usage_scope") == "session":
            self._session_usage = event.usage
        elif event.details.get("usage_scope") == "turn":
            self._turn_usages.append(event.usage)

    def _process_output(self, event: NormalizedEvent) -> None:
        if not event.output_bytes or event.raw_event_type == "stderr":
            return
        self.outputs.append(
            OutputAttribution(
                label=event_label(
                    event.category,
                    event.tool_name,
                    event.command,
                    event.file_path,
                ),
                output_bytes=event.output_bytes,
                estimated_next_turn_tokens=math.ceil(event.output_bytes / 4),
                category=event.category,
            )
        )
        self.outputs.sort(key=lambda item: item.output_bytes, reverse=True)
        del self.outputs[100:]

    def _process_span(self, event: NormalizedEvent) -> None:
        if event.event_type in {"process", "turn", "session"} and event.duration_ms is None:
            return
        if event.details.get("replace_estimated_category") is True:
            self.spans = [
                span
                for span in self.spans
                if not (span.category == event.category and span.measurement == "estimated")
            ]
            self.open_events = {
                key: started
                for key, started in self.open_events.items()
                if not (started.category == event.category and started.measurement == "estimated")
            }
        correlation = event.correlation_id
        if correlation and event.status == "started":
            self.open_events[correlation] = event
            return
        if correlation and event.status in _FINISHED:
            started = self.open_events.pop(correlation, None)
            if started is not None:
                self.spans.append(
                    Span(
                        correlation_id=correlation,
                        category=started.category,
                        started_at=started.timestamp,
                        ended_at=max(event.timestamp, started.timestamp),
                        label=event_label(
                            started.category,
                            started.tool_name,
                            started.command,
                            started.file_path,
                        ),
                        measurement=(
                            "estimated"
                            if "estimated" in {started.measurement, event.measurement}
                            else started.measurement
                        ),
                        agent_id=started.agent_id or event.agent_id,
                    )
                )
                return
        if event.duration_ms is not None and event.duration_ms > 0:
            self.spans.append(
                Span(
                    correlation_id=correlation or f"explicit:{self.event_count}",
                    category=event.category,
                    started_at=event.timestamp - timedelta(milliseconds=event.duration_ms),
                    ended_at=event.timestamp,
                    label=event_label(
                        event.category,
                        event.tool_name,
                        event.command,
                        event.file_path,
                    ),
                    measurement=event.measurement,
                    agent_id=event.agent_id,
                )
            )

    def _update_status(self, event: NormalizedEvent) -> None:
        if event.event_type in {"provider_stderr", "usage"}:
            return
        if event.event_type in {"process", "session"} and event.status in _FINISHED:
            self.current_status = "Failed" if event.status == "failed" else "Completed"
            self.current_event = None
        elif event.status in {"started", "in_progress"}:
            self.current_event = event
            self.current_status = event_label(
                event.category, event.tool_name, event.command, event.file_path
            )
        elif event.status == "failed":
            self.current_status = "Error"

    def finalize(self) -> None:
        if self.finalized:
            return
        ended_at = self.last_timestamp
        if ended_at is not None:
            for correlation, started in list(self.open_events.items()):
                self.spans.append(
                    Span(
                        correlation_id=correlation,
                        category=started.category,
                        started_at=started.timestamp,
                        ended_at=max(ended_at, started.timestamp),
                        label=event_label(
                            started.category,
                            started.tool_name,
                            started.command,
                            started.file_path,
                        ),
                        measurement=started.measurement,
                        agent_id=started.agent_id,
                        incomplete=True,
                    )
                )
        self.open_events.clear()
        self.finalized = True

    def token_usage(self) -> TokenUsage:
        if self._session_usage is not None:
            return self._session_usage

        def total(field: str) -> int | None:
            values = [getattr(usage, field) for usage in self._turn_usages]
            if any(value is not None for value in values):
                return sum(value or 0 for value in values)
            return None

        return TokenUsage(
            actual_input_tokens=total("actual_input_tokens"),
            actual_cached_input_tokens=total("actual_cached_input_tokens"),
            actual_cache_write_input_tokens=total("actual_cache_write_input_tokens"),
            actual_output_tokens=total("actual_output_tokens"),
            actual_reasoning_tokens=total("actual_reasoning_tokens"),
        )

    def inclusive_ms(self) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for span in self.spans:
            result[span.category] += span.duration_ms
        return dict(result)

    def exclusive_ms(self) -> dict[str, int]:
        if not self.spans:
            return {}
        points = sorted(
            {point for span in self.spans for point in (span.started_at, span.ended_at)}
        )
        allocated: dict[str, float] = defaultdict(float)
        for left, right in pairwise(points):
            if right <= left:
                continue
            active = {
                span.category
                for span in self.spans
                if span.started_at < right and span.ended_at > left
            }
            if not active:
                continue
            duration = (right - left).total_seconds() * 1000
            share = duration / len(active)
            for category in active:
                allocated[category] += share
        return {category: round(value) for category, value in allocated.items()}

    def elapsed_ms(self) -> int:
        if self.first_timestamp is None or self.last_timestamp is None:
            return 0
        return max(
            0,
            round((self.last_timestamp - self.first_timestamp).total_seconds() * 1000),
        )

    def summary(self) -> dict[str, Any]:
        inclusive = self.inclusive_ms()
        exclusive = self.exclusive_ms()
        active_wall = sum(exclusive.values())
        elapsed = self.elapsed_ms()
        usage = self.token_usage()
        return {
            "schema_version": 1,
            "elapsed_ms": elapsed,
            "inclusive_ms": inclusive,
            "exclusive_ms": exclusive,
            "idle_or_unclassified_ms": max(0, elapsed - active_wall),
            "tokens": usage.to_dict(),
            "largest_outputs": [item.to_dict() for item in self.outputs[:10]],
            "event_count": self.event_count,
            "span_count": len(self.spans),
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "incomplete_span_count": sum(span.incomplete for span in self.spans),
            "spans": [span.to_dict() for span in self.spans],
            "time_accounting": {
                "inclusive": "sum of spans; parallel work can double-count wall time",
                "exclusive": "overlap-adjusted wall time split equally across active categories",
            },
        }
