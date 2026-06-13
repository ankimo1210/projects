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
name need this (currently just `gto`).
"""

import gto  # noqa: F401
