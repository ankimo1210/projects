"""TOML, environment, and defaults for Agent Profiler."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_config_path, user_data_path


@dataclass(slots=True)
class DisplayConfig:
    refresh_ms: int = 250
    show_estimates: bool = True
    max_timeline_rows: int = 20


@dataclass(slots=True)
class StorageConfig:
    save_raw_events: bool = True
    retention_days: int = 30
    max_event_bytes: int = 2 * 1024 * 1024


@dataclass(slots=True)
class PrivacyConfig:
    redact_secrets: bool = True


@dataclass(slots=True)
class ProviderConfig:
    enabled: bool = True


@dataclass(slots=True)
class CcusageConfig:
    enabled: bool = True
    executable: str = "ccusage"


@dataclass(slots=True)
class AppConfig:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    codex: ProviderConfig = field(default_factory=ProviderConfig)
    claude: ProviderConfig = field(default_factory=ProviderConfig)
    ccusage: CcusageConfig = field(default_factory=CcusageConfig)
    data_dir: Path = field(
        default_factory=lambda: user_data_path("agent-profiler", "agent-profiler")
    )


def default_config_path() -> Path:
    return user_config_path("agent-profiler", "agent-profiler") / "config.toml"


def _boolean(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def load_config(path: Path | None = None) -> AppConfig:
    explicit = path or (
        Path(os.environ["AGENT_PROFILER_CONFIG"])
        if "AGENT_PROFILER_CONFIG" in os.environ
        else default_config_path()
    )
    data: dict[str, Any] = {}
    if explicit.is_file():
        with explicit.open("rb") as handle:
            loaded = tomllib.load(handle)
        data = loaded if isinstance(loaded, dict) else {}

    display = _section(data, "display")
    storage = _section(data, "storage")
    privacy = _section(data, "privacy")
    providers = _section(data, "providers")
    ccusage = _section(data, "ccusage")
    config = AppConfig(
        display=DisplayConfig(
            refresh_ms=int(display.get("refresh_ms", 250)),
            show_estimates=bool(display.get("show_estimates", True)),
            max_timeline_rows=int(display.get("max_timeline_rows", 20)),
        ),
        storage=StorageConfig(
            save_raw_events=bool(storage.get("save_raw_events", True)),
            retention_days=int(storage.get("retention_days", 30)),
            max_event_bytes=int(storage.get("max_event_bytes", 2 * 1024 * 1024)),
        ),
        privacy=PrivacyConfig(redact_secrets=bool(privacy.get("redact_secrets", True))),
        codex=ProviderConfig(enabled=bool(_section(providers, "codex").get("enabled", True))),
        claude=ProviderConfig(enabled=bool(_section(providers, "claude").get("enabled", True))),
        ccusage=CcusageConfig(
            enabled=bool(ccusage.get("enabled", True)),
            executable=str(ccusage.get("executable", "ccusage")),
        ),
    )

    env = os.environ
    if "AGENT_PROFILER_DATA_DIR" in env:
        config.data_dir = Path(env["AGENT_PROFILER_DATA_DIR"]).expanduser()
    if "AGENT_PROFILER_REFRESH_MS" in env:
        config.display.refresh_ms = int(env["AGENT_PROFILER_REFRESH_MS"])
    if "AGENT_PROFILER_SAVE_RAW_EVENTS" in env:
        config.storage.save_raw_events = _boolean(env["AGENT_PROFILER_SAVE_RAW_EVENTS"])
    if "AGENT_PROFILER_RETENTION_DAYS" in env:
        config.storage.retention_days = int(env["AGENT_PROFILER_RETENTION_DAYS"])
    if "AGENT_PROFILER_REDACT_SECRETS" in env:
        config.privacy.redact_secrets = _boolean(env["AGENT_PROFILER_REDACT_SECRETS"])

    if config.display.refresh_ms < 50:
        raise ValueError("display.refresh_ms must be at least 50")
    if config.storage.retention_days < 0:
        raise ValueError("storage.retention_days must be non-negative")
    if config.storage.max_event_bytes < 64 * 1024:
        raise ValueError("storage.max_event_bytes must be at least 65536")
    return config
