"""Resolve personal data from machine-local configuration, never Git settings."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

INPUT_FILES = (
    "portfolio.private.json",
    "ibkr-transactions.private.csv",
    "securities-transactions.private.csv",
    "dc-holding.private.json",
    "dc-transactions.private.tsv",
    "ibkr-ledger.private.json",
)


def config_file() -> Path:
    name = (
        "windows.json"
        if os.name == "nt"
        else ("wsl.json" if os.environ.get("WSL_DISTRO_NAME") else "config.json")
    )
    return Path.home() / ".config" / "portfolio-analyzer" / name


def _external(project: Path, directory: Path) -> Path:
    if not directory.is_absolute():
        raise ValueError("Private data directory must be an absolute path outside the repository")
    directory = directory.resolve()
    public = next((p for p in (project, *project.parents) if (p / ".git").exists()), project)
    if directory.is_relative_to(public.resolve()):
        raise ValueError("Private data directory must be outside the public repository")
    return directory


def data_dir(project: Path, *, config: Path | None = None) -> Path:
    override = os.environ.get("PORTFOLIO_PRIVATE_DATA_DIR")
    if override is not None:
        return _external(project, Path(override).expanduser())
    path = config if config is not None else config_file()
    if not path.is_file():
        return project / "data"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value["schema_version"] != 1 or not isinstance(value["data_dir"], str):
            raise ValueError
        directory = Path(value["data_dir"]).expanduser()
    except (ValueError, KeyError, TypeError):
        raise ValueError("Invalid private data configuration") from None
    return _external(project, directory)


def configure(project: Path, directory: Path, *, config: Path | None = None) -> Path:
    directory = _external(project, directory.expanduser())
    if not directory.is_dir():
        raise ValueError("Private data directory does not exist")
    path = config if config is not None else config_file()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".private-path-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema_version": 1, "data_dir": str(directory)}, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".private-input-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def refresh_inputs(source: Path, cache: Path, *, connection_root: Path) -> bool:
    """Copy the shared inputs in one direction; reject local edits."""
    source, cache = source.resolve(), cache.resolve()
    connection_root = connection_root.resolve()
    if not source.is_relative_to(connection_root):
        raise ValueError("Drive connection point must contain the input directory")
    if source.is_relative_to(cache) or cache.is_relative_to(source):
        raise ValueError("Drive and local copy must be separate directories")
    state_file = cache / ".input-source-state.json"
    previous = {}
    if state_file.is_file():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            previous = state["files"]
            if state["schema_version"] != 1 or set(previous) != set(INPUT_FILES):
                raise ValueError
            if not all(
                isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in previous.values()
            ):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise ValueError("Invalid verified copy record") from None

    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    if not source.is_dir():
        if connection_root.is_dir():
            raise ValueError("Input directory is missing from the connected Drive")
        if not previous or not all(
            (cache / name).is_file() and digest((cache / name).read_bytes()) == previous[name]
            for name in INPUT_FILES
        ):
            raise ValueError("No complete verified local copy is available")
        return False
    if not all((source / name).is_file() for name in INPUT_FILES):
        raise ValueError("An input is missing from the connected Drive; copy not updated")
    incoming = {name: (source / name).read_bytes() for name in INPUT_FILES}
    hashes = {name: digest(payload) for name, payload in incoming.items()}
    for name in INPUT_FILES:
        path = cache / name
        if path.exists():
            current = digest(path.read_bytes())
            if current != hashes[name] and current != previous.get(name):
                raise ValueError("Local inputs have changed; copy not overwritten")
    for name, payload in incoming.items():
        _atomic_bytes(cache / name, payload)
    _atomic_bytes(state_file, (json.dumps({"schema_version": 1, "files": hashes}) + "\n").encode())
    return True
