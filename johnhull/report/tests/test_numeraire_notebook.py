"""M29 protects all M28 cells and the complete conditional numeraire lesson."""

import importlib
import json

import nbformat


def test_numeraire_notebook_and_four_negative_controls():
    m = importlib.import_module("johnhull.scripts.verify_numeraire_notebook")
    assert m.RECORD.parent.name == "section-28-4"
    assert m.NOTEBOOK.parent.name == "10_exotics_martingales"
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 257 and len(m._outside(nb)) == 246
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == m.KEYS
    outputs = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "12 source requirements" in outputs
    assert "OIS annuity unchanged by projection basis: True" in outputs


def test_numeraire_dependency_covers_whole_parent_section():
    m = importlib.import_module("johnhull.scripts.verify_numeraire_notebook")
    f = importlib.import_module("johnhull.scripts.evidence_fingerprint")
    spec = json.loads((m.PROJECT / "scripts/evidence_dependencies.json").read_text())["sections"][
        "28.4"
    ]
    cells, _ = f.notebook_slice(
        json.loads(m.NOTEBOOK.read_text()), spec["notebook"]["heading"], spec["notebook"]["level"]
    )
    text = "\n".join(c["source"] for c in cells)
    for n in range(1, 7):
        assert f"### 6C.{n} " in text
    assert spec["book"]["level"] == spec["notebook"]["level"] == 2
    assert spec["book"]["heading"] == spec["notebook"]["heading"]
