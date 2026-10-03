"""M27 protects all M26 cells and the complete new factor lesson."""

import importlib
import json

import nbformat


def test_factor_notebook_and_four_negative_controls():
    m = importlib.import_module("johnhull.scripts.verify_factor_risk_notebook")
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 235 and len(m._outside(nb)) == 224
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == m.KEYS
    outputs = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "Example 28.3: excess=6.000000%" in outputs
    assert "Synthetic r=4%: total=10.000000%" in outputs


def test_factor_dependency_covers_whole_parent_section():
    m = importlib.import_module("johnhull.scripts.verify_factor_risk_notebook")
    f = importlib.import_module("johnhull.scripts.evidence_fingerprint")
    spec = json.loads((m.PROJECT / "scripts/evidence_dependencies.json").read_text())["sections"][
        "28.2"
    ]
    cells, _ = f.notebook_slice(
        json.loads(m.NOTEBOOK.read_text()), spec["notebook"]["heading"], spec["notebook"]["level"]
    )
    text = "\n".join(c["source"] for c in cells)
    for n in range(1, 7):
        assert f"### 6A.{n} " in text
    assert spec["book"]["level"] == spec["notebook"]["level"] == 2
    assert spec["book"]["heading"] == spec["notebook"]["heading"]
