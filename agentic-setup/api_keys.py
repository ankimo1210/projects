"""Read selected API keys from a private Drive folder or its local copy."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "reinfolib": "REINFOLIB_API_KEY",
}
DEFAULT_CONFIG = Path.home() / ".config" / "repo-secrets" / "config.json"


class SecretError(Exception):
    """A diagnostic that must never contain a credential value."""


@dataclass(frozen=True)
class Config:
    source_dir: Path | None
    cache_dir: Path
    public_root: Path | None = None


def _provider(name: str) -> str:
    if name not in PROVIDERS:
        raise SecretError("Unsupported provider.")
    return PROVIDERS[name]


def _repository_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    return None


def _validate_paths(config: Config) -> None:
    public_root = config.public_root or _repository_root()
    repositories = [public_root.resolve()] if public_root is not None else []
    paths = [config.cache_dir] + ([config.source_dir] if config.source_dir else [])
    resolved = [path.expanduser().resolve() for path in paths]
    if any(path.is_relative_to(repository) for repository in repositories for path in resolved):
        raise SecretError("Secret storage must be outside the public repository.")
    if len(resolved) == 2:
        cache, source = resolved
        if cache.is_relative_to(source) or source.is_relative_to(cache):
            raise SecretError("Drive and local secret folders must be separate.")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".api-key-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_config(config: Config, path: Path = DEFAULT_CONFIG) -> None:
    _validate_paths(config)
    payload = {
        "schema_version": 1,
        "source_dir": str(config.source_dir) if config.source_dir else None,
        "cache_dir": str(config.cache_dir),
        "public_root": str(config.public_root or _repository_root())
        if config.public_root or _repository_root()
        else None,
    }
    _atomic_write(path, (json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def read_config(path: Path = DEFAULT_CONFIG) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data["schema_version"] != 1:
            raise SecretError("Unsupported configuration version.")
        config = Config(
            Path(data["source_dir"]) if data["source_dir"] else None,
            Path(data["cache_dir"]),
            Path(data["public_root"]) if data.get("public_root") else None,
        )
        _validate_paths(config)
        return config
    except (OSError, ValueError, KeyError, TypeError):
        raise SecretError("Private API-key configuration is missing or invalid.") from None


def _validate_key(value: str) -> str:
    if not isinstance(value, str):
        raise SecretError("An API key must be text.")
    stripped = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_./+=-]{8,4096}", stripped):
        raise SecretError("Invalid API-key format; the value has not been logged.")
    return stripped


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_retired(folder: Path) -> dict[str, list[str]]:
    path = folder / ".retired.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError
        for name, fingerprints in data.items():
            _provider(name)
            if not isinstance(fingerprints, list) or not all(
                isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item)
                for item in fingerprints
            ):
                raise ValueError
        return data
    except (ValueError, TypeError):
        raise SecretError("The retired-key record is invalid.") from None


def _merged_retired(config: Config) -> dict[str, list[str]]:
    records = _read_retired(config.cache_dir)
    if config.source_dir and config.source_dir.is_dir():
        for provider, fingerprints in _read_retired(config.source_dir).items():
            records[provider] = sorted(set(records.get(provider, [])) | set(fingerprints))
    return records


def _parse_env(provider: str, text: str) -> str | None:
    expected = _provider(provider)
    result = None
    seen = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name.strip() != expected or seen:
            raise SecretError(f"Unexpected setting in the {provider} key file.")
        seen = True
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result = _validate_key(value) if value else None
    return result


def retire_key(config: Config, provider: str, value: str) -> None:
    _validate_paths(config)
    variable = _provider(provider)
    value = _validate_key(value)
    if not config.source_dir or not config.source_dir.is_dir():
        raise SecretError("Connect the private Drive folder before retiring a key.")
    existing = _merged_retired(config)
    digest = _fingerprint(value)
    existing[provider] = sorted(set(existing.get(provider, [])) | {digest})
    payload = (json.dumps(existing, indent=2) + "\n").encode()
    folders = [config.source_dir, config.cache_dir]
    data = f"{variable}={value}\n".encode()
    for folder in folders:
        archive = folder / "retired" / f"{provider}.env"
        if archive.exists() and archive.read_bytes() != data:
            raise SecretError("A different retired key is already archived.")
    for folder in folders:
        archive = folder / "retired" / f"{provider}.env"
        _atomic_write(archive, data)
        _atomic_write(folder / ".retired.json", payload)


def save_keys(config: Config, values: dict[str, str]) -> list[str]:
    _validate_paths(config)
    if not isinstance(values, dict):
        raise SecretError("Expected a provider-to-key object.")
    selected = {}
    for provider, value in values.items():
        _provider(provider)
        if not isinstance(value, str):
            raise SecretError("An API key must be text.")
        if value.strip():
            selected[provider] = _validate_key(value)
    if not selected:
        return []
    if not config.source_dir or not config.source_dir.is_dir():
        raise SecretError("Connect the private Drive folder before saving keys.")
    retired = _merged_retired(config)
    for provider, value in selected.items():
        if _fingerprint(value) in retired.get(provider, []):
            raise SecretError(f"The {provider} key is retired; enter a newly issued key.")
    record = (json.dumps(retired, indent=2) + "\n").encode()
    for folder in [config.source_dir, config.cache_dir]:
        _atomic_write(folder / ".retired.json", record)
    for provider, value in selected.items():
        data = f"{PROVIDERS[provider]}={value}\n".encode()
        _atomic_write(config.source_dir / f"{provider}.env", data)
        _atomic_write(config.cache_dir / f"{provider}.env", data)
    return sorted(selected)


def sync(config: Config) -> bool:
    _validate_paths(config)
    if not config.source_dir or not config.source_dir.is_dir():
        return False
    retired = _merged_retired(config)
    pending = []
    for provider in PROVIDERS:
        source = config.source_dir / f"{provider}.env"
        if not source.is_file():
            # A missing file on an available Drive is not an offline fallback.
            # Disable the cached key so it cannot reappear after disconnection.
            pending.append((config.cache_dir / source.name, f"{PROVIDERS[provider]}=\n".encode()))
            continue
        data = source.read_bytes()
        try:
            value = _parse_env(provider, data.decode("utf-8-sig"))
        except UnicodeError:
            raise SecretError(f"The {provider} key file is not UTF-8.") from None
        if value and _fingerprint(value) in retired.get(provider, []):
            raise SecretError(f"The {provider} key is retired.")
        pending.append((config.cache_dir / source.name, data))
    _atomic_write(
        config.cache_dir / ".retired.json", (json.dumps(retired, indent=2) + "\n").encode()
    )
    for path, data in pending:
        _atomic_write(path, data)
    return True


def read_key(config: Config, provider: str) -> str:
    _provider(provider)
    _validate_paths(config)
    if config.source_dir and config.source_dir.is_dir():
        if not (config.source_dir / f"{provider}.env").is_file():
            raise SecretError(f"The {provider} key file is missing from the connected Drive.")
    path = config.cache_dir / f"{provider}.env"
    if not path.is_file():
        raise SecretError(f"The {provider} API key has not been registered.")
    try:
        value = _parse_env(provider, path.read_text(encoding="utf-8-sig"))
    except UnicodeError:
        raise SecretError(f"The {provider} key file is not UTF-8.") from None
    if not value:
        raise SecretError(f"The {provider} API key has not been registered.")
    if _fingerprint(value) in _merged_retired(config).get(provider, []):
        raise SecretError(f"The {provider} key is retired.")
    return value


def status(config: Config) -> dict:
    result = {}
    retired = _merged_retired(config)
    source_available = bool(config.source_dir and config.source_dir.is_dir())
    for provider in PROVIDERS:
        try:
            read_key(config, provider)
            configured = True
            issue = None
        except (SecretError, OSError):
            configured = False
            missing = source_available and not (config.source_dir / f"{provider}.env").is_file()
            issue = "missing_in_drive" if missing else "not_registered_or_invalid"
        result[provider] = {
            "configured": configured,
            "rotation_required": bool(retired.get(provider)) and not configured,
            "issue": issue,
        }
    return {
        "source_available": source_available,
        "providers": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--source", type=Path)
    init.add_argument("--cache", type=Path, required=True)
    sub.add_parser("status")
    sub.add_parser("sync")
    sub.add_parser("save-json", help="Read key values from standard input, never arguments.")
    set_command = sub.add_parser("set")
    set_command.add_argument("--provider", choices=PROVIDERS, required=True)
    run = sub.add_parser("run")
    run.add_argument("--provider", choices=PROVIDERS, action="append", required=True)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "init":
            config = Config(arguments.source, arguments.cache)
            _validate_paths(config)
            if config.source_dir:
                if not config.source_dir.parent.is_dir():
                    raise SecretError("The selected Drive parent folder does not exist.")
                config.source_dir.mkdir(exist_ok=True, mode=0o700)
                for provider, variable in PROVIDERS.items():
                    path = config.source_dir / f"{provider}.env"
                    if not path.exists():
                        _atomic_write(path, f"{variable}=\n".encode())
            write_config(config, arguments.config)
            sync(config)
            print(json.dumps(status(config)))
            return 0
        config = read_config(arguments.config)
        if arguments.command == "save-json":
            try:
                data = json.load(sys.stdin)
            except ValueError:
                raise SecretError("Invalid key input; no values were logged.") from None
            saved = save_keys(config, data)
            print(json.dumps({"saved": saved, **status(config)}))
        elif arguments.command == "set":
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    value = getpass.getpass(f"{arguments.provider} API key (hidden): ")
            except (getpass.GetPassWarning, EOFError):
                raise SecretError(
                    "Hidden terminal input is unavailable; use the local setup screen."
                ) from None
            print(json.dumps({"saved": save_keys(config, {arguments.provider: value})}))
        elif arguments.command == "sync":
            print(json.dumps({"synced": sync(config), **status(config)}))
        elif arguments.command == "status":
            print(json.dumps(status(config)))
        elif arguments.command == "run":
            command = arguments.argv
            if command and command[0] == "--":
                command = command[1:]
            if not command:
                raise SecretError("A command is required after --.")
            sync(config)
            environment = dict(os.environ)
            for variable in PROVIDERS.values():
                environment.pop(variable, None)
            for provider in set(arguments.provider):
                environment[PROVIDERS[provider]] = read_key(config, provider)
            return subprocess.run(command, env=environment, shell=False, check=False).returncode
        return 0
    except SecretError as error:
        print(f"API key configuration: {error}", file=sys.stderr)
        return 2
    except OSError:
        print("API key storage or command is unavailable; values were not logged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
