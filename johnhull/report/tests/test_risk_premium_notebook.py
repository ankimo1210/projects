"""M26 preserves every M25 cell while expanding the signed-risk explanation."""

import importlib
import json

import nbformat


def test_market_risk_notebook_and_four_negative_controls():
    m = importlib.import_module("johnhull.scripts.verify_risk_premium_notebook")
    nb = nbformat.read(m.NOTEBOOK, as_version=4)
    assert len(nb.cells) == 224 and len(m._outside(nb)) == 213
    assert m.compare(nb, m._base(), m._fresh()) == []
    assert all(row["rejected"] for row in m.negative_controls(nb, m._base(), m._fresh()))
    assert set(m._saved(nb)) == m.KEYS
    text = "\n".join(c.source for c in nb.cells if c.cell_type == "markdown")
    for phrase in ("符号付き", "消費財", "金額比率", "局所", "正規化しない", "年"):
        assert phrase in text
    outputs = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "Example 28.1: lambda=0.200000" in outputs
    assert "Example 28.2: lambda=-0.150000, mu2=1.500000%" in outputs


def test_d1_declaration_covers_all_six_market_risk_subsections():
    gate = importlib.import_module("johnhull.scripts.verify_risk_premium_notebook")
    fingerprint = importlib.import_module("johnhull.scripts.evidence_fingerprint")
    config = json.loads((gate.PROJECT / "scripts/evidence_dependencies.json").read_text())
    spec = config["sections"]["28.1"]
    notebook = json.loads(gate.NOTEBOOK.read_text())
    cells, _ = fingerprint.notebook_slice(
        notebook, spec["notebook"]["heading"], spec["notebook"]["level"]
    )
    text = "\n".join(c["source"] for c in cells)
    for number in range(1, 7):
        assert f"### 6.{number} " in text
    # Book uses the same parent section so sibling subsections are all included.
    assert spec["book"]["heading"] == spec["notebook"]["heading"]
    assert spec["book"]["level"] == spec["notebook"]["level"] == 2
