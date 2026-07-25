"""Claude Code ``stream-json`` adapter.

The CLI envelope is intentionally parsed defensively. The public Claude Agent
SDK defines message/content types, while the CLI reference does not promise a
stable exhaustive JSONL schema.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_profiler.adapters.base import ProviderAdapter
from agent_profiler.classify import (
    classify_tool,
    extract_command,
    extract_file_path,
)
from agent_profiler.models import NormalizedEvent, TokenUsage, parse_timestamp


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class ClaudeAdapter(ProviderAdapter):
    provider = "claude"

    def __init__(self) -> None:
        self.session_id: str | None = None
        self.model: str | None = None
        self.provider_version: str | None = None
        self._wait_sequence = 0
        self._active_wait: str | None = None

    def _event(
        self,
        received_at: datetime,
        raw_type: str,
        raw: dict[str, Any],
        **kwargs: Any,
    ) -> NormalizedEvent:
        timestamp, source = parse_timestamp(raw.get("timestamp"), received_at)
        session = raw.get("session_id", raw.get("sessionId", self.session_id))
        session_id = session if isinstance(session, str) else self.session_id
        return NormalizedEvent(
            timestamp=timestamp,
            timestamp_source=source,
            provider=self.provider,
            session_id=session_id,
            raw_event_type=raw_type,
            **kwargs,
        )

    def _start_wait(
        self, received_at: datetime, raw_type: str, raw: dict[str, Any]
    ) -> NormalizedEvent:
        self._wait_sequence += 1
        self._active_wait = f"model-wait:{self._wait_sequence}"
        return self._event(
            received_at,
            raw_type,
            raw,
            event_type="model_wait",
            category="model_wait",
            status="started",
            correlation_id=self._active_wait,
            measurement="estimated",
            details={"basis": "inter-event gap pending result.duration_api_ms"},
        )

    def _finish_wait(
        self, received_at: datetime, raw_type: str, raw: dict[str, Any]
    ) -> list[NormalizedEvent]:
        if self._active_wait is None:
            return []
        correlation_id = self._active_wait
        self._active_wait = None
        return [
            self._event(
                received_at,
                raw_type,
                raw,
                event_type="model_wait",
                category="model_wait",
                status="completed",
                correlation_id=correlation_id,
                measurement="estimated",
                details={"basis": "inter-event gap pending result.duration_api_ms"},
            )
        ]

    def normalize(self, raw: dict[str, Any], received_at: datetime) -> list[NormalizedEvent]:
        raw_type = str(raw.get("type", "unknown"))
        try:
            if raw_type == "system":
                return self._normalize_system(raw, received_at)
            if raw_type == "assistant":
                return self._normalize_assistant(raw, received_at)
            if raw_type == "user":
                return self._normalize_user(raw, received_at)
            if raw_type == "result":
                return self._normalize_result(raw, received_at)
            if raw_type == "rate_limit_event":
                info = raw.get("rate_limit_info")
                return [
                    self._event(
                        received_at,
                        raw_type,
                        raw,
                        event_type="retry",
                        status="failed",
                        details={
                            "reason": "rate_limit",
                            "status": info.get("status") if isinstance(info, dict) else None,
                        },
                    )
                ]
            if raw_type == "stream_event":
                return [
                    self._event(
                        received_at,
                        raw_type,
                        raw,
                        event_type="model_stream",
                        category="model_wait",
                        status="in_progress",
                        measurement="estimated",
                    )
                ]
        except (TypeError, ValueError, KeyError) as exc:
            return [
                self._event(
                    received_at,
                    raw_type,
                    raw,
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
                raw,
                event_type="unknown",
                category="other",
                details={"preserved": True},
                measurement="unknown",
            )
        ]

    def _normalize_system(
        self, raw: dict[str, Any], received_at: datetime
    ) -> list[NormalizedEvent]:
        subtype = str(raw.get("subtype", "unknown"))
        raw_type = f"system.{subtype}"
        if subtype == "init":
            session = raw.get("session_id")
            self.session_id = session if isinstance(session, str) else self.session_id
            model = raw.get("model")
            self.model = model if isinstance(model, str) else self.model
            version = raw.get("claude_code_version")
            self.provider_version = version if isinstance(version, str) else self.provider_version
            return [
                self._event(
                    received_at,
                    raw_type,
                    raw,
                    event_type="session",
                    status="started",
                    event_id=self.session_id,
                    details={
                        "model": self.model,
                        "provider_version": self.provider_version,
                        "permission_mode": raw.get("permissionMode"),
                    },
                ),
                self._start_wait(received_at, raw_type, raw),
            ]
        if subtype in {"task_started", "task_progress", "task_notification"}:
            task_id = raw.get("task_id", raw.get("tool_use_id"))
            status = {
                "task_started": "started",
                "task_progress": "in_progress",
                "task_notification": "completed",
            }[subtype]
            return [
                self._event(
                    received_at,
                    raw_type,
                    raw,
                    event_type="subagent",
                    category="subagent",
                    status=status,
                    event_id=task_id if isinstance(task_id, str) else None,
                    correlation_id=task_id if isinstance(task_id, str) else None,
                    agent_id=(
                        raw.get("agent_id") if isinstance(raw.get("agent_id"), str) else None
                    ),
                    parent_agent_id=(
                        raw.get("parent_tool_use_id")
                        if isinstance(raw.get("parent_tool_use_id"), str)
                        else None
                    ),
                    details={
                        "subagent_type": raw.get("subagent_type"),
                        "tool_count": raw.get("tool_count"),
                    },
                )
            ]
        duration = _integer(raw.get("duration_ms", raw.get("durationMs")))
        return [
            self._event(
                received_at,
                raw_type,
                raw,
                event_type="system",
                status="completed",
                duration_ms=duration,
                details={"subtype": subtype},
            )
        ]

    def _normalize_assistant(
        self, raw: dict[str, Any], received_at: datetime
    ) -> list[NormalizedEvent]:
        message = raw.get("message")
        message = message if isinstance(message, dict) else {}
        model = message.get("model")
        if isinstance(model, str) and model != "<synthetic>":
            self.model = model
        parent = raw.get("parent_tool_use_id")
        parent_agent_id = parent if isinstance(parent, str) else None
        events = self._finish_wait(received_at, "assistant", raw) if parent_agent_id is None else []
        usage = self._usage(message.get("usage"))
        if usage is not None:
            events.append(
                self._event(
                    received_at,
                    "assistant.usage",
                    raw,
                    event_type="usage",
                    usage=usage,
                    details={"usage_scope": "turn", "model": self.model},
                )
            )
        content = message.get("content")
        if not isinstance(content, list):
            content = []
        error = raw.get("error")
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", "unknown"))
            if block_type in {"tool_use", "server_tool_use"}:
                tool_id = block.get("id")
                tool_name = block.get("name")
                tool_input = block.get("input")
                input_dict = tool_input if isinstance(tool_input, dict) else {}
                name = tool_name if isinstance(tool_name, str) else block_type
                command = extract_command(input_dict)
                file_path = extract_file_path(input_dict)
                category = classify_tool(name, input_dict)
                events.append(
                    self._event(
                        received_at,
                        f"assistant.{block_type}",
                        raw,
                        event_type="tool",
                        category=category,
                        status="started",
                        event_id=tool_id if isinstance(tool_id, str) else None,
                        correlation_id=tool_id if isinstance(tool_id, str) else None,
                        tool_name=name,
                        command=command,
                        file_path=file_path,
                        parent_agent_id=parent_agent_id,
                        details={"server_tool": block_type == "server_tool_use"},
                    )
                )
            elif block_type == "thinking":
                events.append(
                    self._event(
                        received_at,
                        "assistant.thinking",
                        raw,
                        event_type="reasoning",
                        category="reasoning",
                        status="completed",
                        parent_agent_id=parent_agent_id,
                        measurement="unknown",
                    )
                )
            elif block_type == "text":
                events.append(
                    self._event(
                        received_at,
                        "assistant.text",
                        raw,
                        event_type="message",
                        category="other",
                        status="completed" if error is None else "failed",
                        parent_agent_id=parent_agent_id,
                        details={"error": error},
                    )
                )
        if not events:
            events.append(
                self._event(
                    received_at,
                    "assistant",
                    raw,
                    event_type="message",
                    status="failed" if error else "completed",
                    details={"error": error},
                )
            )
        return events

    def _normalize_user(self, raw: dict[str, Any], received_at: datetime) -> list[NormalizedEvent]:
        message = raw.get("message")
        message = message if isinstance(message, dict) else {}
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        events: list[NormalizedEvent] = []
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            correlation = block.get("tool_use_id")
            body = block.get("content")
            encoded = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
            events.append(
                self._event(
                    received_at,
                    "user.tool_result",
                    raw,
                    event_type="tool",
                    status="failed" if block.get("is_error") is True else "completed",
                    event_id=correlation if isinstance(correlation, str) else None,
                    correlation_id=correlation if isinstance(correlation, str) else None,
                    output_bytes=len(encoded),
                    parent_agent_id=(
                        raw.get("parent_tool_use_id")
                        if isinstance(raw.get("parent_tool_use_id"), str)
                        else None
                    ),
                )
            )
        if events:
            if not isinstance(raw.get("parent_tool_use_id"), str):
                events.append(self._start_wait(received_at, "user.tool_result", raw))
            return events
        return [
            self._event(
                received_at,
                "user",
                raw,
                event_type="user",
                category="user_wait",
                status="completed",
            )
        ]

    def _normalize_result(
        self, raw: dict[str, Any], received_at: datetime
    ) -> list[NormalizedEvent]:
        usage = self._usage(raw.get("usage"))
        duration_api_ms = _integer(raw.get("duration_api_ms"))
        status = "failed" if raw.get("is_error") is True else "completed"
        events = self._finish_wait(received_at, "result", raw)
        if duration_api_ms is not None:
            events.append(
                self._event(
                    received_at,
                    "result.api_duration",
                    raw,
                    event_type="model_wait",
                    category="model_wait",
                    status="completed",
                    duration_ms=duration_api_ms,
                    measurement="actual",
                    details={
                        "basis": "Claude result.duration_api_ms",
                        "replace_estimated_category": True,
                    },
                )
            )
        events.append(
            self._event(
                received_at,
                "result",
                raw,
                event_type="session",
                status=status,
                usage=usage,
                details={
                    "usage_scope": "session",
                    "duration_ms": _integer(raw.get("duration_ms")),
                    "cost_usd": raw.get("total_cost_usd"),
                    "terminal_reason": raw.get("terminal_reason"),
                    "api_error_status": raw.get("api_error_status"),
                    "model_usage_available": isinstance(raw.get("modelUsage"), dict),
                },
            )
        )
        return events

    @staticmethod
    def _usage(value: object) -> TokenUsage | None:
        if not isinstance(value, dict):
            return None
        return TokenUsage(
            actual_input_tokens=_integer(value.get("input_tokens")),
            actual_cached_input_tokens=_integer(value.get("cache_read_input_tokens")),
            actual_cache_write_input_tokens=_integer(value.get("cache_creation_input_tokens")),
            actual_output_tokens=_integer(value.get("output_tokens")),
            actual_reasoning_tokens=_integer(value.get("reasoning_output_tokens")),
        )
