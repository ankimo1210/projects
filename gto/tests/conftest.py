"""Shared pytest setup for the gto suite.

The maturin-built native extensions ``gto_py`` / ``gto_cuda`` are not in the uv
lockfile, so a plain ``uv sync`` (run by any agent sharing the venv) removes
them. Several modules import them at load time
(``gto.api.main`` -> routers -> ``import gto_py``;
``gto.library.batch`` -> ``import gto_cuda``;
``gto.solver.multistreet_gpu`` -> both), which makes the whole suite fail at
*collection* time when the extensions are absent — even for tests that never
touch the solver.

When the real extensions are present we leave them alone. When they are absent
we register an empty stand-in so import-time ``import gto_py`` / ``import
gto_cuda`` succeed; tests that actually need the bindings already guard on
``hasattr(gto_py, "solve_hu_river")`` and skip.
"""

from __future__ import annotations

import sys
import types


def _ensure_stub(name: str) -> None:
    try:
        __import__(name)
    except ImportError:
        sys.modules[name] = types.ModuleType(name)


for _mod in ("gto_py", "gto_cuda"):
    _ensure_stub(_mod)
