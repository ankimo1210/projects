"""Guard: every public deep_hedge_price API carries a docstring."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "deep_hedge_price"
MODULES = sorted(p for p in SRC.glob("*.py") if p.name != "__init__.py")


def _undocumented(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    missing: list[str] = []
    if not ast.get_docstring(tree):
        missing.append("<module>")

    def visit(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if not ast.get_docstring(node):
                    missing.append(prefix + node.name)
                if isinstance(node, ast.ClassDef):
                    visit(node.body, prefix + node.name + ".")

    visit(tree.body, "")
    return missing


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.stem)
def test_public_api_documented(path: Path) -> None:
    missing = _undocumented(path)
    assert not missing, f"{path.name}: undocumented public API: {missing}"
