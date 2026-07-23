"""Best-effort secret redaction for provider events and previews."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY = re.compile(
    r"(^|[_-])(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|token|"
    r"password|passwd|secret|credential|cookie|set[_-]?cookie|env|environment|"
    r"environment[_-]?variables)($|[_-])",
    re.IGNORECASE,
)
_VALUE_PATTERNS = (
    re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b([A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY))"
        r"(\s*=\s*)([^\s\"']+)"
    ),
)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _VALUE_PATTERNS:
        if pattern.groups >= 3:
            redacted = pattern.sub(r"\1\2" + REDACTED, redacted)
        else:
            redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact(value: Any) -> Any:
    """Return a redacted copy without mutating provider input."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            string_key = str(key)
            result[string_key] = REDACTED if _SENSITIVE_KEY.search(string_key) else redact(child)
        return result
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(child) for child in value]
    return value
