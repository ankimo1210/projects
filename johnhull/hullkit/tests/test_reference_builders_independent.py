"""Independent reference builders must not reach hullkit, even through sibling scripts.

A runtime ``sys.modules`` check passes only until someone adds a function-level
import, so read the source of every builder and of the scripts it imports.
"""

import ast
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
BUILDERS = sorted(SCRIPTS.glob("build_*_reference.py"))


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module
            if node.level or node.module is None:
                yield from (alias.name for alias in node.names)


def _reaches_hullkit(path, seen):
    if path in seen:
        return []
    seen.add(path)
    found = []
    for name in _imports(path):
        if name.split(".")[0] == "hullkit":
            found.append(f"{path.name}: {name}")
        sibling = SCRIPTS / f"{name.split('.')[-1]}.py"
        if sibling.is_file():
            found += _reaches_hullkit(sibling, seen)
    return found


def test_builders_are_found():
    assert {"build_cliquet_reference.py", "build_compound_reference.py"} <= {
        path.name for path in BUILDERS
    }


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda path: path.stem)
def test_reference_builder_does_not_import_hullkit(builder):
    assert _reaches_hullkit(builder, set()) == []
