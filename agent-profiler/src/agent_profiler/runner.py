"""Async provider process runner with bounded JSONL ingestion."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_profiler.adapters import adapter_for
from agent_profiler.ccusage import CcusageAdapter
from agent_profiler.config import AppConfig
from agent_profiler.metrics import MetricsEngine
from agent_profiler.models import NormalizedEvent
from agent_profiler.privacy import redact, redact_text
from agent_profiler.report import build_report
from agent_profiler.storage import SessionStore

EventCallback = Callable[[NormalizedEvent, str], None]


@dataclass(slots=True)
class RunResult:
    profiler_session_id: str
    session_path: Path
    provider_session_id: str | None
    exit_code: int
    summary: dict[str, Any]
    model: str | None
    provider_version: str | None


def provider_argv(provider: str, prompt: str) -> list[str]:
    if provider == "codex":
        return ["codex", "exec", "--json", prompt]
    if provider == "claude":
        return [
            "claude",
            "-p",
            prompt,
            "--verbose",
            "--output-format",
            "stream-json",
            "--forward-subagent-text",
        ]
    raise ValueError(f"unsupported provider: {provider}")


def provider_passthrough_argv(provider: str, args: list[str]) -> list[str]:
    """Build a structured-output command while preserving provider arguments."""

    if provider != "codex":
        raise ValueError(f"passthrough is not supported for provider: {provider}")
    if not args:
        raise ValueError("codex passthrough requires arguments after exec")
    prefix = ["codex", "exec"]
    if "--json" not in args:
        prefix.append("--json")
    return [*prefix, *args]


def provider_version(provider: str) -> str | None:
    executable = "codex" if provider == "codex" else "claude"
    if shutil.which(executable) is None:
        return None
    try:
        process = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return process.stdout.strip() or process.stderr.strip() or None


async def bounded_lines(
    reader: asyncio.StreamReader, max_bytes: int
) -> AsyncIterator[tuple[bytes | None, int]]:
    """Yield complete lines or ``(None, discarded_bytes)`` for oversized lines."""

    while True:
        try:
            line = await reader.readuntil(b"\n")
        except asyncio.IncompleteReadError as exc:
            if exc.partial:
                if len(exc.partial) <= max_bytes:
                    yield exc.partial, 0
                else:
                    yield None, len(exc.partial)
            break
        except asyncio.LimitOverrunError as exc:
            discarded = 0
            consume = max(1, exc.consumed)
            chunk = await reader.readexactly(consume)
            discarded += len(chunk)
            while True:
                try:
                    tail = await reader.readuntil(b"\n")
                    discarded += len(tail)
                    break
                except asyncio.LimitOverrunError as nested:
                    consume = max(1, nested.consumed)
                    chunk = await reader.readexactly(consume)
                    discarded += len(chunk)
                except asyncio.IncompleteReadError as nested:
                    discarded += len(nested.partial)
                    break
            yield None, discarded
            if reader.at_eof():
                break
            continue
        if len(line) > max_bytes:
            yield None, len(line)
        else:
            yield line.rstrip(b"\r\n"), 0


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGINT)
        else:
            process.send_signal(signal.SIGINT)
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=3)
        return
    except TimeoutError:
        pass
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except TimeoutError:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


def _sanitize_event(event: NormalizedEvent, enabled: bool) -> NormalizedEvent:
    if not enabled:
        return event
    value = redact(event.to_dict())
    if not isinstance(value, dict):
        return event
    return NormalizedEvent.from_dict(value)


def _raw_preview(raw: dict[str, Any], redact_secrets: bool) -> str:
    value = redact(raw) if redact_secrets else raw
    rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return rendered if len(rendered) <= 4_096 else rendered[:4_093] + "..."


async def run_provider(
    provider: str,
    prompt: str,
    config: AppConfig,
    *,
    cwd: Path,
    callback: EventCallback | None = None,
) -> RunResult:
    return await _run_provider_command(
        provider,
        provider_argv(provider, prompt),
        config,
        cwd=cwd,
        callback=callback,
    )


async def run_provider_args(
    provider: str,
    args: list[str],
    config: AppConfig,
    *,
    cwd: Path,
    callback: EventCallback | None = None,
) -> RunResult:
    """Run an existing provider invocation with structured output enabled."""

    return await _run_provider_command(
        provider,
        provider_passthrough_argv(provider, args),
        config,
        cwd=cwd,
        callback=callback,
    )


async def _run_provider_command(
    provider: str,
    command: list[str],
    config: AppConfig,
    *,
    cwd: Path,
    callback: EventCallback | None = None,
) -> RunResult:
    enabled = config.codex.enabled if provider == "codex" else config.claude.enabled
    if not enabled:
        raise ValueError(f"{provider} provider is disabled by configuration")
    executable = "codex" if provider == "codex" else "claude"
    if shutil.which(executable) is None:
        raise FileNotFoundError(f"{executable} executable was not found on PATH")
    if not cwd.is_dir():
        raise FileNotFoundError(f"working directory does not exist: {cwd}")

    version = provider_version(provider)
    adapter = adapter_for(provider)
    adapter.provider_version = version
    metrics = MetricsEngine()
    store = SessionStore(config.data_dir)
    store.prune(config.storage.retention_days)
    recorder = store.recorder(
        provider,
        {
            "cwd": str(cwd.resolve()),
            "provider_command": executable,
            "prompt_saved": False,
            "provider_version_at_start": version,
        },
        save_raw=config.storage.save_raw_events,
        redact_secrets=config.privacy.redact_secrets,
    )
    process: asyncio.subprocess.Process | None = None
    exit_code = 1

    def emit(event: NormalizedEvent, preview: str) -> None:
        safe_event = _sanitize_event(event, config.privacy.redact_secrets)
        recorder.write_normalized(safe_event)
        metrics.process(safe_event)
        if callback is not None:
            callback(safe_event, preview)

    async def consume_stdout(reader: asyncio.StreamReader) -> None:
        async for line, discarded in bounded_lines(reader, config.storage.max_event_bytes):
            received_at = datetime.now(UTC)
            if line is None:
                raw = {
                    "_agent_profiler": "oversized_event_discarded",
                    "discarded_bytes": discarded,
                }
                recorder.write_raw(raw)
                event = NormalizedEvent(
                    timestamp=received_at,
                    provider=provider,
                    event_type="oversized_event",
                    status="failed",
                    output_bytes=discarded,
                    raw_event_type="invalid.oversized",
                    measurement="unknown",
                    details={"discarded": True},
                )
                emit(event, _raw_preview(raw, config.privacy.redact_secrets))
                continue
            text = line.decode("utf-8", errors="replace")
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                raw = {
                    "_agent_profiler": "invalid_jsonl",
                    "preview": redact_text(text[:512])
                    if config.privacy.redact_secrets
                    else text[:512],
                }
                recorder.write_raw(raw)
                event = NormalizedEvent(
                    timestamp=received_at,
                    provider=provider,
                    event_type="parse_error",
                    status="failed",
                    output_bytes=len(line),
                    raw_event_type="invalid.json",
                    measurement="unknown",
                )
                emit(event, _raw_preview(raw, config.privacy.redact_secrets))
                continue
            if not isinstance(loaded, dict):
                loaded = {"_agent_profiler": "non_object_json", "value": loaded}
            recorder.write_raw(loaded)
            preview = _raw_preview(loaded, config.privacy.redact_secrets)
            events = adapter.normalize(loaded, received_at)
            for index, event in enumerate(events):
                emit(event, preview if index == 0 else "")

    async def consume_stderr(reader: asyncio.StreamReader) -> None:
        async for line, discarded in bounded_lines(reader, config.storage.max_event_bytes):
            received_at = datetime.now(UTC)
            if line is None:
                text = f"[stderr line discarded: {discarded} bytes]"
            else:
                text = line.decode("utf-8", errors="replace")
            raw = {"_stream": "stderr", "text": text}
            recorder.write_raw(raw)
            event = NormalizedEvent(
                timestamp=received_at,
                provider=provider,
                event_type="provider_stderr",
                status="in_progress",
                output_bytes=discarded or len(text.encode("utf-8")),
                raw_event_type="stderr",
                details={"preview": text[:512]},
            )
            emit(event, _raw_preview(raw, config.privacy.redact_secrets))

    emit(
        NormalizedEvent(
            timestamp=datetime.now(UTC),
            provider=provider,
            event_type="process",
            status="started",
            raw_event_type="agent_profiler.process.started",
            tool_name=f"{provider} startup",
        ),
        "",
    )
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=os.name == "posix",
            limit=config.storage.max_event_bytes + 1,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        await asyncio.gather(
            consume_stdout(process.stdout),
            consume_stderr(process.stderr),
        )
        exit_code = await process.wait()
    except asyncio.CancelledError:
        if process is not None:
            await asyncio.shield(_stop_process(process))
        exit_code = 130
    finally:
        if process is not None and process.returncode is None:
            await _stop_process(process)
        emit(
            NormalizedEvent(
                timestamp=datetime.now(UTC),
                provider=provider,
                session_id=adapter.session_id,
                event_type="process",
                status="completed" if exit_code == 0 else "failed",
                raw_event_type="agent_profiler.process.completed",
                details={"exit_code": exit_code},
            ),
            "",
        )
        metrics.finalize()
        summary = metrics.summary()
        if exit_code != 0 and summary["error_count"] == 0:
            summary["error_count"] = 1
        reconciled: dict[str, Any] | None = None
        if config.ccusage.enabled:
            usage = await asyncio.to_thread(
                CcusageAdapter(config.ccusage.executable).reconcile,
                provider,
                adapter.session_id,
            )
            if usage is not None:
                reconciled = usage.to_dict()
                summary["reconciled_tokens"] = reconciled
        report_metadata = dict(recorder.metadata)
        report_metadata.update(
            {
                "model": adapter.model,
                "provider_version": adapter.provider_version or version,
            }
        )
        report = build_report(report_metadata, summary)
        recorder.finalize(
            summary,
            report,
            exit_code=exit_code,
            provider_session_id=adapter.session_id,
            model=adapter.model,
            provider_version=adapter.provider_version or version,
            reconciled_usage=reconciled,
        )
    return RunResult(
        profiler_session_id=recorder.session_id,
        session_path=recorder.path,
        provider_session_id=adapter.session_id,
        exit_code=exit_code,
        summary=summary,
        model=adapter.model,
        provider_version=adapter.provider_version or version,
    )
