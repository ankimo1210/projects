from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_profiler.adapters.claude import ClaudeAdapter
from agent_profiler.adapters.codex import CodexAdapter

FIXTURES = Path(__file__).parent / "fixtures"
START = datetime(2026, 1, 1, tzinfo=UTC)


def _load(name: str) -> list[dict[str, object]]:
    values = []
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        values.append(json.loads(line))
    return values


def test_codex_normal_session_and_usage() -> None:
    adapter = CodexAdapter()
    events = []
    for index, raw in enumerate(_load("codex-session.jsonl")):
        events.extend(adapter.normalize(raw, START + timedelta(seconds=index)))
    command = next(event for event in events if event.correlation_id == "cmd-2")
    assert command.category == "test"
    command_events = [event for event in events if event.correlation_id == "cmd-2"]
    assert [event.status for event in command_events] == ["started", "completed"]
    assert next(event for event in events if event.correlation_id == "cmd-1").category == "search"
    assert command.timestamp_source == "received"
    usage = next(event.usage for event in events if event.usage is not None)
    assert usage.actual_cached_input_tokens == 800
    assert usage.actual_reasoning_tokens == 40
    assert adapter.session_id == "codex-fixture-session"


def test_codex_unknown_event_is_preserved() -> None:
    event = CodexAdapter().normalize({"type": "future.event", "x": 1}, START)[0]
    assert event.event_type == "unknown"
    assert event.category == "other"
    assert event.details["preserved"] is True


def test_claude_tools_parallel_subagent_and_session_usage() -> None:
    adapter = ClaudeAdapter()
    events = []
    for raw in _load("claude-session.jsonl"):
        events.extend(adapter.normalize(raw, START))
    starts = [event for event in events if event.event_type == "tool"]
    assert {event.correlation_id for event in starts} >= {"tool-1", "tool-2"}
    assert next(event for event in starts if event.correlation_id == "tool-1").category == "read"
    assert next(event for event in starts if event.correlation_id == "tool-2").category == "test"
    assert any(event.category == "subagent" for event in events)
    result = next(event for event in events if event.raw_event_type == "result" and event.usage)
    assert result.usage is not None
    assert result.usage.actual_cached_input_tokens == 81
    assert result.details["usage_scope"] == "session"
    assert adapter.model == "claude-test-model"
    assert adapter.provider_version == "2.1.218"
    assert any(event.category == "model_wait" and event.status == "started" for event in events)


def test_claude_missing_usage_and_timestamp_do_not_fail() -> None:
    event = ClaudeAdapter().normalize(
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}},
        START,
    )[0]
    assert event.timestamp == START
    assert event.timestamp_source == "received"


def test_claude_session_id_version_variant() -> None:
    event = ClaudeAdapter().normalize(
        {"type": "user", "sessionId": "legacy-id", "message": {"content": "text"}},
        START,
    )[0]
    assert event.session_id == "legacy-id"
