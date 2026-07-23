"""Textual live view for provider runs and fixture replay."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, ClassVar

from rich.table import Table
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, RichLog, Static, TabbedContent, TabPane
from textual.worker import Worker

from agent_profiler.metrics import MetricsEngine
from agent_profiler.models import NormalizedEvent
from agent_profiler.report import format_count, format_duration
from agent_profiler.runner import RunResult

RunnerFactory = Callable[[Callable[[NormalizedEvent, str], None]], Awaitable[RunResult]]


class AgentTopApp(App[RunResult | None]):
    CSS = """
    Screen { layout: vertical; }
    #summary { height: 10; padding: 0 1; }
    #body { height: 1fr; }
    DataTable, RichLog { height: 1fr; }
    """
    TITLE = "agenttop"
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("q", "request_stop", "Quit / interrupt"),
        ("m", "show_tab('metrics')", "Metrics"),
        ("l", "show_tab('events')", "Events"),
    ]

    def __init__(
        self,
        provider: str,
        runner_factory: RunnerFactory,
        *,
        refresh_ms: int = 250,
        max_timeline_rows: int = 20,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.runner_factory = runner_factory
        self.refresh_ms = refresh_ms
        self.max_timeline_rows = max_timeline_rows
        self.events: list[NormalizedEvent] = []
        self.live_metrics = MetricsEngine()
        self.result: RunResult | None = None
        self._worker: Worker[RunResult] | None = None
        self._started = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Starting…", id="summary")
        with TabbedContent(id="body", initial="metrics"):
            with TabPane("Metrics", id="metrics"):
                yield DataTable(id="timeline", zebra_stripes=True)
            with TabPane("Event log", id="events"):
                yield RichLog(id="event-log", wrap=False, highlight=True, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timeline", DataTable)
        table.add_columns("Time", "Category", "Status", "Current tool / command", "Value")
        self.set_interval(self.refresh_ms / 1000, self._refresh_summary)
        self._worker = self.run_worker(self._execute(), exclusive=True, name="provider-run")

    async def _execute(self) -> RunResult:
        result = await self.runner_factory(self.on_profiler_event)
        self.result = result
        self.live_metrics.finalize()
        self._refresh_summary()
        await asyncio.sleep(0.35)
        self.exit(result)
        return result

    def on_profiler_event(self, event: NormalizedEvent, raw_preview: str) -> None:
        self.events.append(event)
        self.live_metrics.process(event)
        if len(self.events) > 2_000:
            del self.events[:500]
        if raw_preview:
            self.query_one("#event-log", RichLog).write(raw_preview)
        table = self.query_one("#timeline", DataTable)
        value = ""
        if event.duration_ms is not None:
            value = format_duration(event.duration_ms)
        elif event.output_bytes is not None:
            value = f"{event.output_bytes / 1024:.1f} KB"
        label = event.command or event.file_path or event.tool_name or event.event_type
        marker = "~" if event.measurement == "estimated" else ""
        table.add_row(
            event.timestamp.astimezone().strftime("%H:%M:%S"),
            event.category,
            event.status or "",
            label[:100],
            marker + value,
        )
        while table.row_count > self.max_timeline_rows:
            first_key = next(iter(table.rows))
            table.remove_row(first_key)

    def _refresh_summary(self) -> None:
        if self.result is not None:
            summary = self.result.summary
            model = self.result.model or "unavailable"
            status = "Completed" if self.result.exit_code == 0 else f"Exit {self.result.exit_code}"
        else:
            summary = self._live_summary()
            model = next(
                (
                    str(event.details.get("model"))
                    for event in self.events
                    if event.details.get("model")
                ),
                "detecting…",
            )
            status = self._current_status()
        tokens = summary.get("tokens", {})
        tokens = tokens if isinstance(tokens, dict) else {}
        inclusive = summary.get("inclusive_ms", {})
        inclusive = inclusive if isinstance(inclusive, dict) else {}
        table = Table.grid(expand=True)
        table.add_column(style="bold cyan", width=11)
        table.add_column()
        table.add_row("PROVIDER", f"{self.provider} · {model}")
        table.add_row("STATUS", status)
        table.add_row("ELAPSED", format_duration(summary.get("elapsed_ms", 0)))
        table.add_row(
            "TOKENS",
            "actual: "
            f"in {format_count(tokens.get('actual_input_tokens'))} · "
            f"cached {format_count(tokens.get('actual_cached_input_tokens'))} · "
            f"out {format_count(tokens.get('actual_output_tokens'))} · "
            f"reasoning {format_count(tokens.get('actual_reasoning_tokens'))}",
        )
        table.add_row(
            "TIME",
            f"model/API {self._estimate_marker(summary, 'model_wait')}"
            f"{format_duration(inclusive.get('model_wait', 0))} · "
            f"shell {format_duration(inclusive.get('shell', 0))} · "
            f"test {format_duration(inclusive.get('test', 0))} · "
            "read/search "
            f"{format_duration(int(inclusive.get('read', 0)) + int(inclusive.get('search', 0)))}",
        )
        table.add_row(
            "ACTIVITY",
            f"errors {summary.get('error_count', 0)} · "
            f"retries {summary.get('retry_count', 0)} · "
            f"subagents active {self._active_subagents()}",
        )
        table.add_row(
            "CONTEXT",
            "unavailable (not estimated without an official provider capacity value)",
        )
        table.add_row("LEGEND", "actual values are plain · estimated durations use ~")
        self.query_one("#summary", Static).update(table)

    def _live_summary(self) -> dict[str, Any]:
        if not self.events:
            return {"elapsed_ms": 0, "inclusive_ms": {}, "tokens": {}}
        now = datetime.now(UTC)
        summary = self.live_metrics.summary()
        first = self.live_metrics.first_timestamp or now
        summary["elapsed_ms"] = max(0, round((now - first).total_seconds() * 1000))
        inclusive = dict(summary.get("inclusive_ms", {}))
        for started in self.live_metrics.open_events.values():
            duration = max(0, round((now - started.timestamp).total_seconds() * 1000))
            inclusive[started.category] = int(inclusive.get(started.category, 0)) + duration
        summary["inclusive_ms"] = inclusive
        return summary

    def _current_status(self) -> str:
        return self.live_metrics.current_status

    def _active_subagents(self) -> int:
        return sum(event.category == "subagent" for event in self.live_metrics.open_events.values())

    def _estimate_marker(self, summary: dict[str, Any], category: str) -> str:
        spans = summary.get("spans", [])
        estimated = any(
            isinstance(span, dict)
            and span.get("category") == category
            and span.get("measurement") == "estimated"
            for span in spans
        )
        estimated = estimated or any(
            event.category == category and event.measurement == "estimated"
            for event in self.live_metrics.open_events.values()
        )
        return "~" if estimated else ""

    def action_show_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_request_stop(self) -> None:
        if self._worker is not None and not self._worker.is_finished:
            self._worker.cancel()
            return
        self.exit(self.result)
