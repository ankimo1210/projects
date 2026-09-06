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
name need this (currently `gto`, `health`, `jp_llm_lab`, `labor_ai_quadrant`,
`macrokit`, `optimal_execution`, `quantkit`, and `rough_volatility`).
`quantkit` joined the list when the project was renamed so that its directory
matches the package (2026-06-14); the full-workspace run had been latently
broken since then (single-project runs pick quantkit/pyproject.toml as rootdir
and never hit the shadow).
`labor_ai_quadrant` was created with a matching directory/package name
(2026-08-16) and needs the same treatment from the start; `timesfm_lab`
(2026-09-06) is the same case.
"""

import gto  # noqa: F401
import health  # noqa: F401
import jp_llm_lab  # noqa: F401
import labor_ai_quadrant  # noqa: F401
import macrokit  # noqa: F401
import optimal_execution  # noqa: F401
import quantkit  # noqa: F401
import rough_volatility  # noqa: F401
import timesfm_lab  # noqa: F401


def pytest_configure(config) -> None:
    # macrokit declares this marker in its own pyproject.toml, which is
    # enough for project-scoped runs (rootdir = macrokit). A full-workspace
    # run takes its config from *this* root pyproject instead, which has no
    # `markers` setting, so the marker would otherwise be unknown here and
    # --strict-markers would turn the two live tests into a hard error (or,
    # without --strict-markers, PytestUnknownMarkWarning). Registered the
    # same way rough_volatility/tests/conftest.py registers `slow`.
    config.addinivalue_line(
        "markers", "live: hits a real external API; requires network and API keys"
    )
