from __future__ import annotations

import re
from pathlib import Path

_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def ensure_within_directory(base: Path, target: Path) -> Path:
    """Resolve both paths and raise ValueError if target escapes base."""
    resolved_base = base.resolve()
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {target!r} is outside {base!r}")
    return resolved_target


def safe_filename(name: str) -> str:
    """Convert an arbitrary string to a safe filename."""
    if not name:
        return "unnamed"
    sanitized = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
    # Strip leading dots to avoid hidden files
    sanitized = sanitized.lstrip(".")
    if not sanitized:
        sanitized = "unnamed"
    stem = sanitized.rsplit(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        sanitized = "_" + sanitized
    # Truncate to 200 chars to stay well under filesystem limits
    return sanitized[:200]


def confirm_output_dir(path: Path) -> Path:
    """Ensure output directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def redact_text(value: object, max_len: int = 80) -> str:
    """Trim long text for safe display; collapse newlines."""
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def unique_path(dst: Path) -> Path:
    """Return dst unchanged if it does not exist, otherwise add a numeric suffix."""
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
