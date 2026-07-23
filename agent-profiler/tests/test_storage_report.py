from __future__ import annotations

import json
import stat
from datetime import UTC, datetime, timedelta

from agent_profiler.models import NormalizedEvent
from agent_profiler.report import build_report, format_duration_delta
from agent_profiler.storage import SessionStore


def test_private_storage_redaction_and_report(tmp_path) -> None:
    store = SessionStore(tmp_path)
    recorder = store.recorder(
        "codex",
        {"provider_version": "fixture"},
        save_raw=True,
        redact_secrets=True,
    )
    recorder.write_raw({"authorization": "Bearer secret-value", "type": "fixture"})
    recorder.write_normalized(
        NormalizedEvent(
            timestamp=datetime.now(UTC),
            provider="codex",
            event_type="fixture",
        )
    )
    summary = {
        "elapsed_ms": 1000,
        "inclusive_ms": {},
        "exclusive_ms": {},
        "tokens": {},
        "largest_outputs": [],
        "spans": [],
        "incomplete_span_count": 0,
        "error_count": 0,
        "retry_count": 0,
    }
    report = build_report(recorder.metadata, summary)
    recorder.finalize(
        summary,
        report,
        exit_code=0,
        provider_session_id="provider-id",
        model="model",
        provider_version="1",
    )
    raw = (recorder.path / "events.raw.jsonl").read_text(encoding="utf-8")
    assert "secret-value" not in raw
    assert "[REDACTED]" in raw
    for path in recorder.path.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert store.read_json(recorder.session_id, "summary.json")["elapsed_ms"] == 1000


def test_no_raw_log_omits_raw_file(tmp_path) -> None:
    recorder = SessionStore(tmp_path).recorder("claude", {}, save_raw=False, redact_secrets=True)
    recorder.abort()
    assert not (recorder.path / "events.raw.jsonl").exists()


def test_retention_removes_only_expired_session_directory(tmp_path) -> None:
    store = SessionStore(tmp_path)
    recorder = store.recorder("codex", {}, save_raw=False, redact_secrets=True)
    recorder.metadata["started_at"] = datetime.now(UTC) - timedelta(days=40)
    recorder.finalize(
        {"elapsed_ms": 0},
        "# report\n",
        exit_code=0,
        provider_session_id=None,
        model=None,
        provider_version=None,
    )
    metadata_path = recorder.path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["started_at"] = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    removed = store.prune(30)
    assert removed == [recorder.session_id]
    assert not recorder.path.exists()


def test_duration_delta_preserves_direction() -> None:
    assert format_duration_delta(-2000) == "-2s"
    assert format_duration_delta(2000) == "+2s"
