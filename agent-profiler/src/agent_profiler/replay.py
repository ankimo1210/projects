"""Replay raw JSONL fixtures through the production adapters."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.adapters import adapter_for
from agent_profiler.config import AppConfig
from agent_profiler.metrics import MetricsEngine
from agent_profiler.models import NormalizedEvent, parse_timestamp
from agent_profiler.privacy import redact, redact_text
from agent_profiler.report import build_report
from agent_profiler.runner import EventCallback, RunResult
from agent_profiler.storage import SessionStore


def infer_provider(path: Path) -> str:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            event_type = str(value.get("type", ""))
            if event_type.startswith(("thread.", "turn.", "item.")):
                return "codex"
            if event_type in {
                "system",
                "assistant",
                "user",
                "result",
                "rate_limit_event",
                "stream_event",
            }:
                return "claude"
    raise ValueError("could not infer provider from replay file")


async def replay_file(
    path: Path,
    config: AppConfig,
    *,
    provider: str | None = None,
    speed: float = 1.0,
    callback: EventCallback | None = None,
) -> RunResult:
    if speed <= 0:
        raise ValueError("replay speed must be greater than zero")
    selected = provider or infer_provider(path)
    adapter = adapter_for(selected)
    metrics = MetricsEngine()
    store = SessionStore(config.data_dir)
    recorder = store.recorder(
        selected,
        {
            "source": "replay",
            "replay_file": str(path.resolve()),
            "replay_speed": speed,
            "prompt_saved": False,
        },
        save_raw=config.storage.save_raw_events,
        redact_secrets=config.privacy.redact_secrets,
    )
    previous: datetime | None = None
    parse_errors = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            received_at = datetime.now(UTC)
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                raw = {
                    "_agent_profiler": "invalid_jsonl",
                    "preview": redact_text(line[:512])
                    if config.privacy.redact_secrets
                    else line[:512],
                }
                recorder.write_raw(raw)
                event = NormalizedEvent(
                    timestamp=received_at,
                    provider=selected,
                    event_type="parse_error",
                    status="failed",
                    output_bytes=len(line.encode("utf-8")),
                    raw_event_type="invalid.json",
                    measurement="unknown",
                )
                recorder.write_normalized(event)
                metrics.process(event)
                if callback:
                    callback(event, json.dumps(raw, ensure_ascii=False))
                continue
            if not isinstance(loaded, dict):
                loaded = {"_agent_profiler": "non_object_json", "value": loaded}
            timestamp, timestamp_source = parse_timestamp(loaded.get("timestamp"), received_at)
            if previous is not None and timestamp_source == "provider" and timestamp > previous:
                delay = min((timestamp - previous).total_seconds() / speed, 2.0)
                if delay > 0:
                    await asyncio.sleep(delay)
            elif previous is not None:
                await asyncio.sleep(min(0.05 / speed, 0.1))
            previous = timestamp
            recorder.write_raw(loaded)
            display_raw = redact(loaded) if config.privacy.redact_secrets else loaded
            preview = json.dumps(display_raw, ensure_ascii=False, default=str)
            if len(preview) > 4_096:
                preview = preview[:4_093] + "..."
            events = adapter.normalize(loaded, timestamp)
            for index, event in enumerate(events):
                if config.privacy.redact_secrets:
                    safe = redact(event.to_dict())
                    event = NormalizedEvent.from_dict(safe)
                recorder.write_normalized(event)
                metrics.process(event)
                if callback:
                    callback(event, preview if index == 0 else "")
    metrics.finalize()
    summary = metrics.summary()
    metadata = dict(recorder.metadata)
    metadata.update({"model": adapter.model, "provider_version": adapter.provider_version})
    report = build_report(metadata, summary)
    exit_code = 1 if parse_errors and metrics.event_count == parse_errors else 0
    recorder.finalize(
        summary,
        report,
        exit_code=exit_code,
        provider_session_id=adapter.session_id,
        model=adapter.model,
        provider_version=adapter.provider_version,
    )
    return RunResult(
        profiler_session_id=recorder.session_id,
        session_path=recorder.path,
        provider_session_id=adapter.session_id,
        exit_code=exit_code,
        summary=summary,
        model=adapter.model,
        provider_version=adapter.provider_version,
    )
