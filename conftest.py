"""Workspace-root conftest.

pytest 9 (import-mode=importlib) derives module names for per-project
conftest/test files from the workspace rootdir, e.g. `gto/tests/conftest.py`
becomes "gto.tests.conftest". While materializing the missing parent "gto",
pytest synthesizes a *namespace* module pointing at the project directory
`gto/`, which then shadows the real installed `gto` package in sys.modules
(`from gto.api ...` fails with ModuleNotFoundError in multi-project runs).

Importing the real package here, before any per-project conftest is loaded,
makes pytest reuse it as the parent instead of synthesizing the namespace
shadow. Only projects whose directory name equals their importable package
name need this (currently `gto`, `health`, `quantkit`, `optimal_execution`,
`rough_volatility`, and `jp_llm_lab`).
`quantkit` joined the list when the project was renamed so that its directory
matches the package (2026-06-14); the full-workspace run had been latently
broken since then (single-project runs pick quantkit/pyproject.toml as rootdir
and never hit the shadow).
"""

import gto  # noqa: F401
import health  # noqa: F401
import jp_llm_lab  # noqa: F401
import optimal_execution  # noqa: F401
import quantkit  # noqa: F401
import rough_volatility  # noqa: F401
