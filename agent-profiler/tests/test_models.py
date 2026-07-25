from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agent_profiler.models import NormalizedEvent, TokenUsage


def test_token_total_does_not_double_count_reasoning() -> None:
    usage = TokenUsage(
        actual_input_tokens=10,
        actual_cached_input_tokens=20,
        actual_output_tokens=7,
        actual_reasoning_tokens=3,
    )
    assert usage.actual_total_tokens == 37


def test_negative_token_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        TokenUsage(actual_input_tokens=-1)


def test_normalized_event_round_trip() -> None:
    event = NormalizedEvent(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        provider="codex",
        event_type="test",
        category="test",
        usage=TokenUsage(actual_input_tokens=1),
    )
    restored = NormalizedEvent.from_dict(event.to_dict())
    assert restored.timestamp == event.timestamp
    assert restored.usage is not None
    assert restored.usage.actual_total_tokens == 1
