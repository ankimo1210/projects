from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from agent_profiler.cli_top import _parser
from agent_profiler.config import AppConfig
from agent_profiler.replay import infer_provider, replay_file
from agent_profiler.runner import (
    bounded_lines,
    provider_argv,
    provider_passthrough_argv,
    run_provider,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_provider_commands_use_documented_structured_output_flags() -> None:
    codex = provider_argv("codex", "task")
    claude = provider_argv("claude", "task")
    assert codex[:3] == ["codex", "exec", "--json"]
    assert "--output-format" in claude
    assert "stream-json" in claude
    assert "--forward-subagent-text" in claude


def test_codex_passthrough_preserves_arguments_and_adds_json() -> None:
    assert provider_passthrough_argv("codex", ["-m", "model", "task"]) == [
        "codex",
        "exec",
        "--json",
        "-m",
        "model",
        "task",
    ]
    assert provider_passthrough_argv("codex", ["--json", "task"]) == [
        "codex",
        "exec",
        "--json",
        "task",
    ]


def test_run_options_after_provider_are_not_consumed_as_prompt() -> None:
    args = _parser().parse_args(["run", "codex", "--no-tui", "--no-raw-log", "--", "task"])
    assert args.no_tui is True
    assert args.no_raw_log is True
    assert args.prompt == ["task"]


def test_wrap_preserves_provider_options_after_separator() -> None:
    args = _parser().parse_args(["wrap", "codex", "--", "-m", "model", "task"])
    assert args.provider_args == ["-m", "model", "task"]


def test_provider_inference() -> None:
    assert infer_provider(FIXTURES / "codex-session.jsonl") == "codex"
    assert infer_provider(FIXTURES / "claude-session.jsonl") == "claude"


async def test_replay_creates_complete_session(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    config.storage.save_raw_events = True
    raw_previews = []
    result = await replay_file(
        FIXTURES / "claude-session.jsonl",
        config,
        speed=10_000,
        callback=lambda _event, raw: raw_previews.append(raw) if raw else None,
    )
    assert result.exit_code == 0
    assert result.model == "claude-test-model"
    assert (result.session_path / "summary.json").is_file()
    assert result.summary["tokens"]["actual_cached_input_tokens"] == 81
    assert result.summary["inclusive_ms"]["model_wait"] == 3500
    assert {
        span["measurement"] for span in result.summary["spans"] if span["category"] == "model_wait"
    } == {"actual"}
    assert len(raw_previews) == len(
        (FIXTURES / "claude-session.jsonl").read_text(encoding="utf-8").splitlines()
    )


async def test_incomplete_jsonl_and_open_tool_survive_replay(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path)
    result = await replay_file(
        FIXTURES / "incomplete.jsonl",
        config,
        provider="codex",
        speed=10_000,
    )
    assert result.exit_code == 0
    assert result.summary["error_count"] >= 1
    assert result.summary["incomplete_span_count"] >= 1


async def test_oversized_line_is_discarded_without_unbounded_buffer() -> None:
    reader = asyncio.StreamReader(limit=65)
    reader.feed_data(b"x" * 100 + b"\n" + b"ok\n")
    reader.feed_eof()
    values = [item async for item in bounded_lines(reader, 64)]
    assert values[0][0] is None
    assert values[0][1] == 101
    assert values[1] == (b"ok", 0)


async def test_provider_exit_code_is_propagated(tmp_path, monkeypatch) -> None:
    executable = tmp_path / "codex"
    executable.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo \'codex-cli fixture\'; exit 0; fi\n'
        'echo \'{"type":"thread.started","thread_id":"fixture"}\'\n'
        "exit 7\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    config = AppConfig(data_dir=tmp_path / "data")
    config.ccusage.enabled = False
    result = await run_provider("codex", "task", config, cwd=tmp_path)
    assert result.exit_code == 7
    assert result.summary["error_count"] == 1


@pytest.mark.skipif(os.name != "posix", reason="process-group signal behavior is POSIX-only")
async def test_cancellation_interrupts_child_and_returns_130(tmp_path, monkeypatch) -> None:
    executable = tmp_path / "codex"
    executable.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo \'codex-cli fixture\'; exit 0; fi\n'
        "trap 'exit 130' INT\n"
        'echo \'{"type":"thread.started","thread_id":"fixture"}\'\n'
        "sleep 10\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    config = AppConfig(data_dir=tmp_path / "data")
    config.ccusage.enabled = False
    task = asyncio.create_task(run_provider("codex", "task", config, cwd=tmp_path))
    await asyncio.sleep(0.1)
    task.cancel()
    result = await asyncio.wait_for(task, timeout=5)
    assert result.exit_code == 130
