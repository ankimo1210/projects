"""Shared fixtures: a quick-profile config loaded once per session."""

from __future__ import annotations

from pathlib import Path

import pytest

from optimal_execution.config import Config, load_config

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"


@pytest.fixture(scope="session")
def cfg() -> Config:
    return load_config(CONFIG_DIR / "quick.yaml")


@pytest.fixture(scope="session")
def cfg_default() -> Config:
    return load_config(CONFIG_DIR / "default.yaml")
