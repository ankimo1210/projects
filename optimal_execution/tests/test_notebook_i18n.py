"""Parity guards for the bilingual visual-lab notebooks.

The English and Japanese editions must run the *same computation* (identical
code cells, so identical figures/numbers) while carrying fully translated
prose — the notebook analogue of the standalone reports' shared quantitative
fingerprint.
"""

from __future__ import annotations

import json

from optimal_execution.notebook import NOTEBOOK_LOCALES
from optimal_execution.provenance import PROJECT_ROOT

# The only code cell allowed to differ: the setup caption is localized.
_SETUP_CELL = 1


def _load(locale: str) -> dict:
    path = PROJECT_ROOT / "notebooks" / NOTEBOOK_LOCALES[locale]["source"]
    return json.loads(path.read_text(encoding="utf-8"))


def _src(cell: dict) -> str:
    source = cell["source"]
    return source if isinstance(source, str) else "".join(source)


def _has_cjk(text: str) -> bool:
    return any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" for ch in text)


def test_both_notebook_sources_exist() -> None:
    for locale, spec in NOTEBOOK_LOCALES.items():
        path = PROJECT_ROOT / "notebooks" / spec["source"]
        assert path.exists(), f"missing {locale} notebook: {path}"


def test_structure_matches() -> None:
    en, ja = _load("en"), _load("ja")
    assert len(en["cells"]) == len(ja["cells"])
    assert [c["cell_type"] for c in en["cells"]] == [c["cell_type"] for c in ja["cells"]]


def test_code_cells_are_identical_except_setup() -> None:
    en, ja = _load("en"), _load("ja")
    for i, (a, b) in enumerate(zip(en["cells"], ja["cells"], strict=True)):
        if a["cell_type"] != "code":
            continue
        if i == _SETUP_CELL:
            for token in ("load_config", "artifact_dirs", "cfg.profile"):
                assert token in _src(a) and token in _src(b)
        else:
            assert _src(a) == _src(b), f"code cell {i} diverges between editions"


def test_markdown_is_translated() -> None:
    en, ja = _load("en"), _load("ja")
    for i, (a, b) in enumerate(zip(en["cells"], ja["cells"], strict=True)):
        if a["cell_type"] != "markdown":
            continue
        assert _src(a) != _src(b), f"markdown cell {i} not translated"
        assert _has_cjk(_src(b)), f"markdown cell {i} has no Japanese text"


def test_titles_carry_locale_tokens() -> None:
    en, ja = _load("en"), _load("ja")
    assert NOTEBOOK_LOCALES["en"]["title_token"] in _src(en["cells"][0])
    assert NOTEBOOK_LOCALES["ja"]["title_token"] in _src(ja["cells"][0])
