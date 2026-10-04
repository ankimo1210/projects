"""M28 protects all M27 cells and the complete conditional martingale lesson."""

import importlib
import json

import nbformat


def test_martingale_notebook_and_four_negative_controls():
    m = importlib.import_module("johnhull.scripts.verify_martingale_notebook")
    assert m.RECORD.parent.name == "section-28-3"
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 246 and len(m._outside(nb)) == 235
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == m.KEYS
    outputs = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "Conditional API: 9 states/time combinations" in outputs
    assert "Same synthetic call: 17.2494832790" in outputs


def test_martingale_dependency_covers_whole_parent_section():
    m = importlib.import_module("johnhull.scripts.verify_martingale_notebook")
    f = importlib.import_module("johnhull.scripts.evidence_fingerprint")
    spec = json.loads((m.PROJECT / "scripts/evidence_dependencies.json").read_text())["sections"][
        "28.3"
    ]
    cells, _ = f.notebook_slice(
        json.loads(m.NOTEBOOK.read_text()), spec["notebook"]["heading"], spec["notebook"]["level"]
    )
    text = "\n".join(c["source"] for c in cells)
    for n in range(1, 7):
        assert f"### 6B.{n} " in text
    assert spec["book"]["level"] == spec["notebook"]["level"] == 2
    assert spec["book"]["heading"] == spec["notebook"]["heading"]
