"""Fresh-check vol06 §27.1 outputs and preserve all cells outside lesson 7."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
from verify_core_notebooks import _output_signature, check_committed_outputs, write_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/06_numerical_methods/numerical.ipynb"
RECORD = PROJECT / "docs/validation/section-27-1/notebook-check.json"
BASE = "7cfd0864"
KEYS = {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"}


def _outside_seven(notebook):
    cells = []
    skipping = False
    for cell in notebook.cells:
        if (
            "## 7. BSM を超えるモデルたち" in cell.source
            or "## 7. Black–Scholes–Merton" in cell.source
        ):
            skipping = True
        if skipping and "## 8. Longstaff-Schwartz" in cell.source:
            skipping = False
        if not skipping:
            cells.append(cell)
    return cells


def _saved_figures(notebook):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload.get("layout", {}).get("meta", {}).get("section") == "27.1":
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    """Return findings for freshness, shared figures, and preserved earlier cells."""
    from hullkit._alternative_models_lesson import _figures

    current = nbformat.read(NOTEBOOK, as_version=4)
    base = nbformat.reads(
        subprocess.run(
            ["git", "show", f"{BASE}:johnhull/volumes/06_numerical_methods/numerical.ipynb"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        as_version=4,
    )
    retained, old = _outside_seven(current), _outside_seven(base)
    findings = []
    if [(c.cell_type, c.source) for c in retained] != [(c.cell_type, c.source) for c in old]:
        findings.append("§7以外のセル本文が基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=retained)) != _output_signature(
        nbformat.v4.new_notebook(cells=old)
    ):
        findings.append("§7以外の保存出力が基点と異なる")
    saved = _saved_figures(current)
    if set(saved) != KEYS:
        findings.append(f"§27.1保存図不足: {sorted(KEYS ^ set(saved))}")
    else:
        for key, fig in _figures().items():
            fresh = json.loads(fig.to_json())
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[part], sort_keys=True
                ):
                    findings.append(f"{key}.{part} differs from shared figure")
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-outputs", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write_outputs:
        findings = write_outputs(NOTEBOOK)
    else:
        findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    if args.write_outputs:
        print("PASS: §27.1 outputs rewritten")
        return
    sources = (
        "scripts/verify_alternative_models_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "docs/validation/section-27-1/reference.json",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
    )
    artifacts = (
        "volumes/06_numerical_methods/numerical.ipynb",
        "book/_build/html/notebooks/06_numerical.html",
    )
    record = {
        "section": "27.1",
        "status": "PASS",
        "base": BASE,
        "preserved_cells_outside_lesson": len(
            _outside_seven(nbformat.read(NOTEBOOK, as_version=4))
        ),
        "saved_figures": sorted(KEYS),
        "source_sha256": {file: _digest(PROJECT / file) for file in sources},
        "artifact_sha256": {file: _digest(PROJECT / file) for file in artifacts},
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.is_file() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.1 notebook record stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §27.1 fresh notebook, saved figures, preserved cells")


if __name__ == "__main__":
    main()
