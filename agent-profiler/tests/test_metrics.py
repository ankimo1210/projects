from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent_profiler.adapters.codex import CodexAdapter
from agent_profiler.metrics import MetricsEngine
from agent_profiler.models import NormalizedEvent, TokenUsage

START = datetime(2026, 1, 1, tzinfo=UTC)


def _event(
    seconds: int,
    correlation: str,
    category: str,
    status: str,
    **kwargs: object,
) -> NormalizedEvent:
    return NormalizedEvent(
        timestamp=START + timedelta(seconds=seconds),
        provider="fixture",
        event_type="tool",
        category=category,  # type: ignore[arg-type]
        status=status,
        correlation_id=correlation,
        **kwargs,  # type: ignore[arg-type]
    )


def test_parallel_inclusive_and_overlap_adjusted_exclusive_time() -> None:
    metrics = MetricsEngine()
    for event in (
        _event(0, "a", "read", "started"),
        _event(1, "b", "test", "started"),
        _event(2, "a", "other", "completed"),
        _event(3, "b", "other", "completed"),
    ):
        metrics.process(event)
    metrics.finalize()
    assert metrics.inclusive_ms() == {"read": 2000, "test": 2000}
    assert metrics.exclusive_ms() == {"read": 1500, "test": 1500}
    assert sum(metrics.exclusive_ms().values()) == metrics.elapsed_ms()


def test_open_tool_is_closed_as_incomplete_on_abnormal_end() -> None:
    metrics = MetricsEngine()
    metrics.process(_event(0, "open", "shell", "started"))
    metrics.process(
        NormalizedEvent(
            timestamp=START + timedelta(seconds=2),
            provider="fixture",
            event_type="error",
            status="failed",
        )
    )
    metrics.finalize()
    assert metrics.spans[0].duration_ms == 2000
    assert metrics.spans[0].incomplete is True


def test_session_usage_replaces_turn_sum() -> None:
    metrics = MetricsEngine()
    metrics.process(
        NormalizedEvent(
            timestamp=START,
            provider="claude",
            event_type="usage",
            usage=TokenUsage(actual_input_tokens=5),
            details={"usage_scope": "turn"},
        )
    )
    metrics.process(
        NormalizedEvent(
            timestamp=START,
            provider="claude",
            event_type="session",
            usage=TokenUsage(actual_input_tokens=8),
            details={"usage_scope": "session"},
        )
    )
    assert metrics.token_usage().actual_input_tokens == 8


def test_output_attribution_is_explicitly_estimated() -> None:
    metrics = MetricsEngine()
    metrics.process(
        NormalizedEvent(
            timestamp=START,
            provider="codex",
            event_type="tool",
            category="test",
            output_bytes=40_001,
            tool_name="pytest",
        )
    )
    item = metrics.summary()["largest_outputs"][0]
    assert item["estimated_next_turn_tokens"] == 10_001
    assert item["measurement"] == "estimated"


def test_turn_boundary_is_not_counted_as_other_work() -> None:
    metrics = MetricsEngine()
    metrics.process(
        NormalizedEvent(
            timestamp=START,
            provider="codex",
            event_type="turn",
            status="started",
            correlation_id="turn:1",
        )
    )
    metrics.process(
        NormalizedEvent(
            timestamp=START + timedelta(seconds=2),
            provider="codex",
            event_type="turn",
            status="completed",
            correlation_id="turn:1",
        )
    )
    metrics.finalize()
    assert metrics.spans == []


def test_one_terminal_error_is_not_counted_for_every_failed_message() -> None:
    metrics = MetricsEngine()
    for event_type in ("retry", "message", "session"):
        metrics.process(
            NormalizedEvent(
                timestamp=START,
                provider="claude",
                event_type=event_type,
                status="failed",
            )
        )
    assert metrics.retry_count == 1
    assert metrics.error_count == 1


def test_codex_in_progress_provider_status_pairs_as_started_span() -> None:
    adapter = CodexAdapter()
    metrics = MetricsEngine()
    start = {
        "type": "item.started",
        "item": {
            "id": "cmd",
            "type": "command_execution",
            "command": "uv run pytest",
            "status": "in_progress",
        },
    }
    end = {
        "type": "item.completed",
        "item": {
            "id": "cmd",
            "type": "command_execution",
            "command": "uv run pytest",
            "status": "completed",
            "exit_code": 0,
        },
    }
    for event in adapter.normalize(start, START):
        metrics.process(event)
    for event in adapter.normalize(end, START + timedelta(seconds=2)):
        metrics.process(event)
    metrics.finalize()
    assert metrics.inclusive_ms()["test"] == 2000


def test_process_boundaries_extend_elapsed_without_becoming_work_span() -> None:
    metrics = MetricsEngine()
    metrics.process(
        NormalizedEvent(
            timestamp=START,
            provider="codex",
            event_type="process",
            status="started",
        )
    )
    metrics.process(
        NormalizedEvent(
            timestamp=START + timedelta(seconds=2),
            provider="codex",
            event_type="process",
            status="completed",
        )
    )
    metrics.finalize()
    assert metrics.elapsed_ms() == 2000
    assert metrics.spans == []
    assert metrics.current_status == "Completed"
