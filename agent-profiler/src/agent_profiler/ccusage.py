"""Optional machine-readable ccusage reconciliation."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ReconciledUsage:
    input_tokens: int
    cached_input_tokens: int
    cache_write_input_tokens: int
    output_tokens: int
    total_tokens: int
    source: str
    source_version: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cache_write_input_tokens": self.cache_write_input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "measurement": "reconciled",
            "source": self.source,
            "source_version": self.source_version,
        }


class CcusageAdapter:
    def __init__(self, executable: str = "ccusage") -> None:
        self.executable = executable

    def reconcile(self, provider: str, provider_session_id: str | None) -> ReconciledUsage | None:
        if not provider_session_id or shutil.which(self.executable) is None:
            return None
        try:
            version_process = subprocess.run(
                [self.executable, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = version_process.stdout.strip() or None
            process = subprocess.run(
                [
                    self.executable,
                    provider,
                    "session",
                    "--json",
                    "--offline",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if process.returncode != 0:
            return None
        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError:
            return None
        sessions = payload.get("sessions") if isinstance(payload, dict) else None
        if not isinstance(sessions, list):
            return None
        match = next(
            (
                item
                for item in sessions
                if isinstance(item, dict)
                and (
                    str(item.get("sessionId", "")) == provider_session_id
                    or provider_session_id in str(item.get("sessionId", ""))
                    or provider_session_id in str(item.get("sessionFile", ""))
                )
            ),
            None,
        )
        if not isinstance(match, dict):
            return None

        def count(key: str) -> int:
            value = match.get(key, 0)
            return value if isinstance(value, int) else 0

        return ReconciledUsage(
            input_tokens=count("inputTokens"),
            cached_input_tokens=count("cacheReadTokens"),
            cache_write_input_tokens=count("cacheCreationTokens"),
            output_tokens=count("outputTokens"),
            total_tokens=count("totalTokens"),
            source="ccusage JSON",
            source_version=version,
        )
