"""Private-by-default session storage."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from agent_profiler.models import NormalizedEvent
from agent_profiler.privacy import redact

FILE_MODE = 0o600
DIR_MODE = 0o700


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=_json_default)
        handle.write("\n")
    os.chmod(temporary, FILE_MODE)
    temporary.replace(path)
    os.chmod(path, FILE_MODE)


class SessionRecorder:
    def __init__(
        self,
        sessions_root: Path,
        provider: str,
        metadata: dict[str, Any],
        *,
        save_raw: bool,
        redact_secrets: bool,
        session_id: str | None = None,
    ) -> None:
        sessions_root.mkdir(parents=True, exist_ok=True, mode=DIR_MODE)
        os.chmod(sessions_root, DIR_MODE)
        generated = session_id or (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{provider}-{uuid.uuid4().hex[:8]}"
        )
        self.session_id = generated
        self.path = sessions_root / generated
        self.path.mkdir(mode=DIR_MODE)
        os.chmod(self.path, DIR_MODE)
        self.redact_secrets = redact_secrets
        self.save_raw = save_raw
        self.metadata = {
            "schema_version": 1,
            "profiler_session_id": generated,
            "provider": provider,
            "started_at": datetime.now(UTC),
            "raw_events_saved": save_raw,
            "raw_events_redacted": redact_secrets,
            "telemetry_enabled": False,
            **metadata,
        }
        _write_json(self.path / "metadata.json", self.metadata)
        self._normalized = self._open_private(self.path / "events.normalized.jsonl")
        self._raw: TextIO | None = (
            self._open_private(self.path / "events.raw.jsonl") if save_raw else None
        )
        self._closed = False

    @staticmethod
    def _open_private(path: Path) -> TextIO:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
        return os.fdopen(descriptor, "w", encoding="utf-8")

    def write_raw(self, raw: dict[str, Any]) -> None:
        if self._raw is None:
            return
        value = redact(raw) if self.redact_secrets else raw
        json.dump(value, self._raw, ensure_ascii=False, separators=(",", ":"), default=str)
        self._raw.write("\n")

    def write_normalized(self, event: NormalizedEvent) -> None:
        value = event.to_dict()
        if self.redact_secrets:
            value = redact(value)
        json.dump(
            value,
            self._normalized,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        self._normalized.write("\n")

    def finalize(
        self,
        summary: dict[str, Any],
        report: str,
        *,
        exit_code: int,
        provider_session_id: str | None,
        model: str | None,
        provider_version: str | None,
        reconciled_usage: dict[str, Any] | None = None,
    ) -> None:
        if self._closed:
            return
        self._normalized.close()
        if self._raw is not None:
            self._raw.close()
        if reconciled_usage is not None:
            summary["reconciled_tokens"] = reconciled_usage
        _write_json(self.path / "summary.json", summary)
        report_path = self.path / "report.md"
        report_path.write_text(report, encoding="utf-8")
        os.chmod(report_path, FILE_MODE)
        self.metadata.update(
            {
                "finished_at": datetime.now(UTC),
                "exit_code": exit_code,
                "provider_session_id": provider_session_id,
                "model": model,
                "provider_version": provider_version,
            }
        )
        _write_json(self.path / "metadata.json", self.metadata)
        self._closed = True

    def abort(self) -> None:
        if self._closed:
            return
        self._normalized.close()
        if self._raw is not None:
            self._raw.close()
        self._closed = True


class SessionStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.sessions_root = data_dir / "sessions"

    def recorder(
        self,
        provider: str,
        metadata: dict[str, Any],
        *,
        save_raw: bool,
        redact_secrets: bool,
    ) -> SessionRecorder:
        return SessionRecorder(
            self.sessions_root,
            provider,
            metadata,
            save_raw=save_raw,
            redact_secrets=redact_secrets,
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        if not self.sessions_root.is_dir():
            return []
        sessions: list[dict[str, Any]] = []
        for directory in self.sessions_root.iterdir():
            metadata_path = directory / "metadata.json"
            if not directory.is_dir() or not metadata_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            metadata["path"] = str(directory)
            sessions.append(metadata)
        return sorted(
            sessions,
            key=lambda item: str(item.get("started_at", "")),
            reverse=True,
        )

    def session_path(self, session_id: str) -> Path:
        if Path(session_id).name != session_id:
            raise ValueError("invalid session id")
        path = self.sessions_root / session_id
        if not path.is_dir():
            raise FileNotFoundError(f"session not found: {session_id}")
        return path

    def read_json(self, session_id: str, name: str) -> dict[str, Any]:
        path = self.session_path(session_id) / name
        if not path.is_file():
            raise FileNotFoundError(f"{name} not found for session {session_id}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{name} is not a JSON object")
        return value

    def prune(self, retention_days: int, now: datetime | None = None) -> list[str]:
        if retention_days <= 0 or not self.sessions_root.is_dir():
            return []
        threshold = (now or datetime.now(UTC)) - timedelta(days=retention_days)
        removed: list[str] = []
        for metadata in self.list_sessions():
            started = metadata.get("started_at")
            try:
                timestamp = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            except ValueError:
                continue
            if timestamp >= threshold:
                continue
            path = self.session_path(str(metadata["profiler_session_id"]))
            if path.parent != self.sessions_root:
                continue
            shutil.rmtree(path)
            removed.append(path.name)
        return removed
