"""Opt-in shell integration for automatic Codex profiling."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

SUPPORTED_SHELLS = ("bash", "zsh")
START_MARKER = "# >>> agenttop codex auto-wrap >>>"
END_MARKER = "# <<< agenttop codex auto-wrap <<<"


def detect_shell(environ: dict[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    shell = Path(values.get("SHELL", "")).name
    if shell not in SUPPORTED_SHELLS:
        supported = ", ".join(SUPPORTED_SHELLS)
        raise ValueError(f"could not detect a supported shell; choose one of: {supported}")
    return shell


def default_rc_path(shell: str, home: Path | None = None) -> Path:
    if shell not in SUPPORTED_SHELLS:
        raise ValueError(f"unsupported shell: {shell}")
    root = Path.home() if home is None else home
    return root / (".bashrc" if shell == "bash" else ".zshrc")


def shell_init(shell: str) -> str:
    if shell not in SUPPORTED_SHELLS:
        raise ValueError(f"unsupported shell: {shell}")
    return r"""# agenttop: automatically profile standard `codex exec ...` runs.
function codex {
    local _agenttop_arg
    local _agenttop_bypass=0

    if [ "${AGENTTOP_AUTO_WRAP:-1}" != "1" ] || [ ! -t 0 ]; then
        command codex "$@"
        return $?
    fi

    case "${1-}" in
        exec|e) ;;
        *)
            command codex "$@"
            return $?
            ;;
    esac

    if [ "$#" -le 1 ] || ! command -v agenttop >/dev/null 2>&1; then
        command codex "$@"
        return $?
    fi

    for _agenttop_arg in "$@"; do
        case "$_agenttop_arg" in
            -h|--help|-V|--version|--json|-)
                _agenttop_bypass=1
                break
                ;;
        esac
    done
    if [ "$_agenttop_bypass" -eq 1 ]; then
        command codex "$@"
        return $?
    fi

    shift
    command agenttop wrap codex -- "$@"
}
"""


def integration_block(shell: str) -> str:
    return f"{START_MARKER}\n{shell_init(shell)}{END_MARKER}\n"


def install_shell_hook(shell: str, rc_path: Path) -> bool:
    block = integration_block(shell)
    current = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
    updated = _replace_or_append_block(current, block)
    if updated == current:
        return False
    _atomic_write(rc_path, updated)
    return True


def uninstall_shell_hook(rc_path: Path) -> bool:
    if not rc_path.exists():
        return False
    current = rc_path.read_text(encoding="utf-8")
    updated = _remove_block(current)
    if updated == current:
        return False
    _atomic_write(rc_path, updated)
    return True


def _replace_or_append_block(current: str, block: str) -> str:
    start = current.find(START_MARKER)
    end = current.find(END_MARKER)
    if (start == -1) != (end == -1):
        raise ValueError("shell rc contains an incomplete agenttop integration block")
    if start != -1:
        if end < start:
            raise ValueError("shell rc contains malformed agenttop integration markers")
        end += len(END_MARKER)
        if end < len(current) and current[end] == "\n":
            end += 1
        return current[:start] + block + current[end:]
    separator = "" if not current or current.endswith("\n") else "\n"
    blank_line = "" if not current else "\n"
    return current + separator + blank_line + block


def _remove_block(current: str) -> str:
    start = current.find(START_MARKER)
    end = current.find(END_MARKER)
    if start == -1 and end == -1:
        return current
    if start == -1 or end == -1 or end < start:
        raise ValueError("shell rc contains malformed agenttop integration markers")
    end += len(END_MARKER)
    if end < len(current) and current[end] == "\n":
        end += 1
    prefix = current[:start]
    suffix = current[end:]
    if prefix.endswith("\n\n") and (not suffix or suffix.startswith("\n")):
        prefix = prefix[:-1]
    return prefix + suffix


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(mode)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
