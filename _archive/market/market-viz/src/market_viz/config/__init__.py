"""Canonical, CWD-independent access to the bundled config files.

The YAML files live inside this package (src/market_viz/config/), so all
paths are resolved from ``__file__`` — never from the working directory.
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent
# src/market_viz/config -> src/market_viz -> src -> market-viz/
PROJECT_ROOT = CONFIG_DIR.parents[2]


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_instruments_config() -> dict:
    """Raw instruments.yaml contents (instruments grouped by asset class)."""
    with open(CONFIG_DIR / "instruments.yaml") as f:
        return yaml.safe_load(f)


def load_instruments() -> list[dict]:
    """All instruments flattened across groups."""
    result: list[dict] = []
    for group in load_instruments_config().get("instruments", {}).values():
        result.extend(group)
    return result
