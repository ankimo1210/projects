"""Provider adapter protocol and factory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from agent_profiler.models import NormalizedEvent


class ProviderAdapter(ABC):
    provider: str
    session_id: str | None = None
    model: str | None = None
    provider_version: str | None = None

    @abstractmethod
    def normalize(self, raw: dict[str, Any], received_at: datetime) -> list[NormalizedEvent]:
        """Normalize one provider event without raising for unknown schemas."""


def adapter_for(provider: str) -> ProviderAdapter:
    if provider == "codex":
        from agent_profiler.adapters.codex import CodexAdapter

        return CodexAdapter()
    if provider == "claude":
        from agent_profiler.adapters.claude import ClaudeAdapter

        return ClaudeAdapter()
    raise ValueError(f"unsupported provider: {provider}")
