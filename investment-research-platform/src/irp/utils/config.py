"""YAML config loading + .env support. Configs live in ``configs/`` and hold all
tunable assumptions (tax rates, universe, data-source settings) so nothing is
hard-coded in the modules.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from .paths import CONFIG_DIR


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (no overwrite).

    A minimal loader to avoid a hard dependency at import time; python-dotenv is
    listed as a dep and may be used directly if preferred.
    """
    path = path or (CONFIG_DIR.parent / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


@cache
def load_config(name: str) -> dict[str, Any]:
    """Load ``configs/<name>.yaml`` (``name`` may include or omit the extension)."""
    fname = name if name.endswith((".yaml", ".yml")) else f"{name}.yaml"
    path = CONFIG_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def env(key: str, default: str | None = None) -> str | None:
    """Read an environment variable (API keys etc.). Returns default if unset."""
    return os.environ.get(key, default)
