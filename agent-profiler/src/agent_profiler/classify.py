"""Conservative tool and command classification."""

from __future__ import annotations

import re
import shlex
from pathlib import PurePath
from typing import Any

from agent_profiler.models import Category

_TEST = re.compile(
    r"(^|[/\s])(pytest|py\.test|tox|nox|jest|vitest|cargo\s+test|go\s+test|"
    r"dotnet\s+test|npm\s+(run\s+)?test|pnpm\s+(run\s+)?test|yarn\s+test|make\s+test)(\s|$)",
    re.IGNORECASE,
)
_SEARCH = re.compile(r"(^|[/\s])(rg|grep|ag|ack|find|fd|git\s+grep|ripgrep)(\s|$)", re.IGNORECASE)
_READ = re.compile(
    r"(^|[/\s])(cat|bat|sed|head|tail|less|more|wc|stat|file|readlink)(\s|$)",
    re.IGNORECASE,
)
_EDIT = re.compile(r"(^|[/\s])(apply_patch|patch|perl\s+-pi|sed\s+-i|tee)(\s|$)", re.IGNORECASE)


def classify_command(command: str | None) -> Category:
    if not command:
        return "shell"
    searchable = command.replace("'", " ").replace('"', " ").replace("`", " ")
    if _TEST.search(searchable):
        return "test"
    if _SEARCH.search(searchable):
        return "search"
    if _EDIT.search(searchable):
        return "edit"
    if _READ.search(searchable):
        return "read"
    return "shell"


def classify_tool(name: str | None, tool_input: dict[str, Any] | None = None) -> Category:
    lowered = (name or "").lower()
    if lowered in {"agent", "task"} or "subagent" in lowered or "collab" in lowered:
        return "subagent"
    if "search" in lowered or lowered in {"grep", "glob"}:
        return "web" if "web" in lowered else "search"
    if lowered in {"read", "view", "ls"} or "read_file" in lowered:
        return "read"
    if lowered in {"edit", "write", "notebookedit"} or any(
        part in lowered for part in ("apply_patch", "write_file", "edit_file")
    ):
        return "edit"
    if "web" in lowered or "fetch" in lowered:
        return "web"
    if lowered in {"bash", "shell", "command_execution"}:
        command = extract_command(tool_input or {})
        return classify_command(command)
    return "other"


def extract_command(tool_input: dict[str, Any]) -> str | None:
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def extract_file_path(tool_input: dict[str, Any]) -> str | None:
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    command = extract_command(tool_input)
    if not command:
        return None
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    for word in reversed(words[1:]):
        if not word.startswith("-") and ("/" in word or "." in PurePath(word).name):
            return word
    return None


def event_label(
    category: Category,
    tool_name: str | None,
    command: str | None,
    file_path: str | None,
) -> str:
    fallback = {
        "model_wait": "Model/API wait",
        "reasoning": "Reasoning",
        "user_wait": "User wait",
    }.get(category, category)
    value = command or file_path or tool_name or fallback
    value = " ".join(value.split())
    return value if len(value) <= 100 else value[:97] + "..."
