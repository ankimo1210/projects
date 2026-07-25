from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.models import NormalizedEvent
from agent_profiler.runner import RunResult
from agent_profiler.tui import AgentTopApp


async def test_tui_starts_and_renders_fixture_event(tmp_path) -> None:
    async def factory(callback):
        callback(
            NormalizedEvent(
                timestamp=datetime.now(UTC),
                provider="codex",
                event_type="tool",
                category="test",
                status="started",
                command="uv run pytest",
            ),
            '{"type":"fixture"}',
        )
        return RunResult(
            profiler_session_id="fixture",
            session_path=Path(tmp_path),
            provider_session_id="provider",
            exit_code=0,
            summary={"elapsed_ms": 1, "inclusive_ms": {}, "tokens": {}},
            model="fixture-model",
            provider_version="fixture-version",
        )

    app = AgentTopApp("codex", factory, refresh_ms=50)
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        assert app.query_one("#timeline").row_count == 1
        assert app.live_metrics.current_status == "uv run pytest"
