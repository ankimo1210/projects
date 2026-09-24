"""Write or verify vol10's §26.17 outputs and preserved earlier lesson cells."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import nbformat
from verify_core_notebooks import _output_signature, check_committed_outputs, write_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
BASE = "f0d25b9e"
PLOTLY_MIME = "application/vnd.plotly.v1+json"
KEYS = {
    "static_boundary",
    "static_ladder",
    "static_boundary_error",
    "static_convergence",
}


def _without_new_section(notebook):
    cells = []
    skipping = False
    for cell in notebook.cells:
        if "### 4.7 静的オプション複製" in cell.source:
            skipping = True
        if skipping and "## 5. マルチンゲールと測度" in cell.source:
            skipping = False
        if not skipping:
            cells.append(cell)
    return cells


def _saved_figures(notebook):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY_MIME)
            if payload and payload.get("layout", {}).get("meta", {}).get("section") == "26.17":
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def check():
    """Return actionable findings from fresh execution and exact figure comparison."""
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from hullkit._static_replication_lesson import _figures

    current = nbformat.read(NOTEBOOK, as_version=4)
    base = nbformat.reads(
        subprocess.run(
            ["git", "show", f"{BASE}:johnhull/volumes/10_exotics_martingales/exotics.ipynb"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        as_version=4,
    )
    old_cells, retained = base.cells, _without_new_section(current)
    findings = []
    if [(cell.cell_type, cell.source) for cell in retained] != [
        (cell.cell_type, cell.source) for cell in old_cells
    ]:
        findings.append("§4.7以外のセル本文が基点と異なる")
    old_nb = nbformat.v4.new_notebook(cells=old_cells)
    retained_nb = nbformat.v4.new_notebook(cells=retained)
    if _output_signature(old_nb) != _output_signature(retained_nb):
        findings.append("§4.7以外のセル出力が基点と異なる")
    saved = _saved_figures(current)
    if set(saved) != KEYS:
        findings.append(f"§26.17の保存図が不足: {sorted(KEYS ^ set(saved))}")
    else:
        for key, figure in _figures().items():
            fresh = json.loads(figure.to_json())
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[part], sort_keys=True
                ):
                    findings.append(f"{key}.{part} が共有図と異なる")
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-outputs", action="store_true")
    args = parser.parse_args()
    if args.write_outputs:
        findings = write_outputs(NOTEBOOK)
    else:
        findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    if not args.write_outputs:
        sources = [
            "scripts/verify_static_replication_notebook.py",
            "scripts/verify_core_notebooks.py",
            "hullkit/src/hullkit/_static_replication_lesson.py",
            "docs/validation/section-26-17/reference.json",
            "volumes/10_exotics_martingales/build_exotics_notebook.py",
            "volumes/10_exotics_martingales/exotics.ipynb",
        ]
        artifacts = [
            "volumes/10_exotics_martingales/exotics.ipynb",
            "book/_build/html/notebooks/10_exotics.html",
        ]

        def digest(file):
            return hashlib.sha256((PROJECT / file).read_bytes()).hexdigest()

        record = {
            "status": "PASS",
            "checked_at": datetime.now(UTC).isoformat(),
            "base_commit": BASE,
            "cells": 125,
            "preserved_cells": 115,
            "saved_figures": sorted(KEYS),
            "checks": [
                "fresh execution",
                "original source and output signatures",
                "four exact Plotly data/layout payloads",
            ],
            "source_sha256": {file: digest(file) for file in sources},
            "artifact_sha256": {file: digest(file) for file in artifacts},
        }
        destination = PROJECT / "docs/validation/section-26-17/notebook-check.json"
        destination.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("PASS: §26.17 notebook " + ("outputs written" if args.write_outputs else "verified"))


if __name__ == "__main__":
    main()
