"""Guard: MODEL_INDEX.md lists every hullkit module and its references resolve."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[2] / "MODEL_INDEX.md"
SRC = Path(__file__).resolve().parents[1] / "src" / "hullkit"
MODULES = sorted(p.stem for p in SRC.glob("*.py") if p.name != "__init__.py")
TEXT = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
REFS = sorted(set(re.findall(r"`(hullkit\.[A-Za-z0-9_.]+):([A-Za-z0-9_]+)`", TEXT)))


def test_index_exists() -> None:
    assert INDEX.exists(), "johnhull/MODEL_INDEX.md is missing"


@pytest.mark.parametrize("module", MODULES)
def test_module_listed(module: str) -> None:
    assert f"hullkit.{module}" in TEXT, f"hullkit.{module} missing from MODEL_INDEX.md"


@pytest.mark.parametrize("ref", REFS, ids=lambda r: f"{r[0]}:{r[1]}")
def test_reference_resolves(ref: tuple[str, str]) -> None:
    module, symbol = ref
    obj = importlib.import_module(module)
    assert hasattr(obj, symbol), f"{module}:{symbol} does not resolve"
