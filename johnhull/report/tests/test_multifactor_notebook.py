"""M30 protects all257 accepted M29 cells and four correlated figures."""

import importlib

import nbformat


def test_multifactor_lesson_and_old_notebook_preserved():
    m = importlib.import_module("johnhull.scripts.verify_multifactor_notebook")
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    chapter = importlib.import_module("johnhull.scripts.chapter_acceptance")
    cfg = chapter.load_config("docs/acceptance/chapters/ch28.json")
    nb.cells = chapter.without_chapter_sections(nb, cfg)
    assert len(nb.cells) == 268 and len(m._outside(nb)) == 257
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == m.KEYS
    outputs = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "132 conditional states" in outputs and "8 mutations PASS" in outputs
