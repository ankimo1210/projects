"""Codex ``exec --json`` adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_profiler.adapters.base import ProviderAdapter
from agent_profiler.classify import classify_command, classify_tool
from agent_profiler.models import NormalizedEvent, TokenUsage, parse_timestamp


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class CodexAdapter(ProviderAdapter):
    provider = "codex"

    def __init__(self) -> None:
        self.session_id: str | None = None
        self.model: str | None = None
        self.provider_version: str | None = None
        self._turn = 0
        self._wait_sequence = 0
        self._active_wait: str | None = None

    def _event(
        self,
        received_at: datetime,
        raw_type: str,
        **kwargs: Any,
    ) -> NormalizedEvent:
        timestamp, source = parse_timestamp(kwargs.pop("provider_timestamp", None), received_at)
        return NormalizedEvent(
            timestamp=timestamp,
            timestamp_source=source,
            provider=self.provider,
            session_id=self.session_id,
            raw_event_type=raw_type,
            **kwargs,
        )

    def _start_wait(self, received_at: datetime, raw_type: str) -> NormalizedEvent:
        self._wait_sequence += 1
        self._active_wait = f"model-wait:{self._turn}:{self._wait_sequence}"
        return self._event(
            received_at,
            raw_type,
            event_type="model_wait",
            category="model_wait",
            status="started",
            correlation_id=self._active_wait,
            measurement="estimated",
            details={"basis": "inter-event gap; provider exposes no API span timestamp"},
        )

    def _finish_wait(self, received_at: datetime, raw_type: str) -> list[NormalizedEvent]:
        if self._active_wait is None:
            return []
        correlation_id = self._active_wait
        self._active_wait = None
        return [
            self._event(
                received_at,
                raw_type,
                event_type="model_wait",
                category="model_wait",
                status="completed",
                correlation_id=correlation_id,
                measurement="estimated",
                details={"basis": "inter-event gap; provider exposes no API span timestamp"},
            )
        ]

    def normalize(self, raw: dict[str, Any], received_at: datetime) -> list[NormalizedEvent]:
        raw_type = str(raw.get("type", "unknown"))
        try:
            if raw_type == "thread.started":
                thread_id = raw.get("thread_id")
                self.session_id = thread_id if isinstance(thread_id, str) else self.session_id
                model = raw.get("model")
                self.model = model if isinstance(model, str) else self.model
                return [
                    self._event(
                        received_at,
                        raw_type,
                        event_type="session",
                        status="started",
                        event_id=self.session_id,
                    )
                ]
            if raw_type == "turn.started":
                self._turn += 1
                return [
                    self._event(
                        received_at,
                        raw_type,
                        event_type="turn",
                        status="started",
                        correlation_id=f"turn:{self._turn}",
                    ),
                    self._start_wait(received_at, raw_type),
                ]
            if raw_type in {"turn.completed", "turn.failed"}:
                events = self._finish_wait(received_at, raw_type)
                usage = self._usage(raw.get("usage"))
                status = "completed" if raw_type == "turn.completed" else "failed"
                events.append(
                    self._event(
                        received_at,
                        raw_type,
                        event_type="turn",
                        status=status,
                        correlation_id=f"turn:{self._turn}",
                        usage=usage,
                        details={"usage_scope": "turn"} if usage else {},
                    )
                )
                return events
            if raw_type == "error":
                events = self._finish_wait(received_at, raw_type)
                events.append(
                    self._event(
                        received_at,
                        raw_type,
                        event_type="error",
                        status="failed",
                        details={"message": self._safe_preview(raw.get("message"))},
                    )
                )
                return events
            if raw_type.startswith("item."):
                return self._normalize_item(raw_type, raw.get("item"), received_at)
        except (TypeError, ValueError, KeyError) as exc:
            return [
                self._event(
                    received_at,
                    raw_type,
                    event_type="adapter_error",
                    status="failed",
                    details={"error": type(exc).__name__},
                    measurement="unknown",
                )
            ]
        return [
            self._event(
                received_at,
                raw_type,
                event_type="unknown",
                category="other",
                details={"preserved": True},
                measurement="unknown",
            )
        ]

    def _normalize_item(
        self, raw_type: str, item_value: object, received_at: datetime
    ) -> list[NormalizedEvent]:
        item = item_value if isinstance(item_value, dict) else {}
        events = self._finish_wait(received_at, raw_type)
        item_type = str(item.get("type", "unknown"))
        item_id = item.get("id") if isinstance(item.get("id"), str) else None
        provider_status = str(item.get("status")) if item.get("status") is not None else None
        status = "started" if raw_type == "item.started" else "completed"
        if raw_type == "item.completed" and provider_status in {
            "failed",
            "cancelled",
            "interrupted",
        }:
            status = provider_status
        command = item.get("command") if isinstance(item.get("command"), str) else None
        tool_name: str | None = None
        file_path: str | None = None
        category = "other"
        details: dict[str, Any] = {"provider_status": provider_status}

        if item_type == "command_execution":
            tool_name = "shell"
            category = classify_command(command)
            exit_code = _integer(item.get("exit_code"))
            details["exit_code"] = exit_code
        elif item_type == "file_change":
            category = "edit"
            tool_name = "file_change"
            changes = item.get("changes")
            if isinstance(changes, list) and changes and isinstance(changes[0], dict):
                path = changes[0].get("path")
                file_path = path if isinstance(path, str) else None
        elif item_type == "mcp_tool_call":
            server = item.get("server")
            name = item.get("tool")
            tool_name = ".".join(str(v) for v in (server, name) if isinstance(v, str))
            arguments = item.get("arguments")
            tool_input = arguments if isinstance(arguments, dict) else {}
            category = classify_tool(tool_name, tool_input)
        elif item_type == "web_search":
            category = "web"
            tool_name = "web_search"
        elif item_type == "reasoning":
            category = "reasoning"
        elif any(word in item_type for word in ("agent", "collab", "subagent")):
            category = "subagent"
            tool_name = item_type

        output = item.get("aggregated_output")
        output_bytes = len(output.encode("utf-8")) if isinstance(output, str) else None
        if output_bytes:
            details["output_preview"] = self._safe_preview(output)

        event = self._event(
            received_at,
            raw_type,
            event_type="item",
            category=category,
            status=status,
            event_id=item_id,
            correlation_id=item_id,
            tool_name=tool_name,
            command=command,
            file_path=file_path,
            output_bytes=output_bytes,
            details=details,
        )
        events.append(event)

        if raw_type == "item.completed" and item_type in {
            "command_execution",
            "mcp_tool_call",
            "web_search",
        }:
            events.append(self._start_wait(received_at, raw_type))
        return events

    @staticmethod
    def _usage(value: object) -> TokenUsage | None:
        if not isinstance(value, dict):
            return None
        return TokenUsage(
            actual_input_tokens=_integer(value.get("input_tokens")),
            actual_cached_input_tokens=_integer(value.get("cached_input_tokens")),
            actual_cache_write_input_tokens=_integer(value.get("cache_write_input_tokens")),
            actual_output_tokens=_integer(value.get("output_tokens")),
            actual_reasoning_tokens=_integer(value.get("reasoning_output_tokens")),
        )

    @staticmethod
    def _safe_preview(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        compact = " ".join(value.split())
        return compact[:512]
