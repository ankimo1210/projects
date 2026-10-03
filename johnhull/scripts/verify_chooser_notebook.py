"""Verify vol10 §4.15 and preserve the complete accepted M24 notebook."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import nbformat

try:
    from .verify_core_notebooks import _output_signature, check_committed_outputs
except ImportError:
    from verify_core_notebooks import _output_signature, check_committed_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
RECORD = PROJECT / "docs/validation/section-26-8/notebook-check.json"
BASE = "5013f2d4"
START = "### 4.15 "
END = "## 5. "
PLOTLY = "application/vnd.plotly.v1+json"
KEYS = {"chooser_choice", "chooser_package", "chooser_timing", "chooser_validation"}


def _outside(notebook):
    kept, skipping = [], False
    for cell in notebook.cells:
        if cell.cell_type == "markdown" and cell.source.startswith(START):
            skipping = True
        if skipping and cell.cell_type == "markdown" and cell.source.startswith(END):
            skipping = False
        if not skipping:
            kept.append(cell)
    return kept


def _base():
    result = subprocess.run(
        ["git", "show", f"{BASE}:johnhull/volumes/10_exotics_martingales/exotics.ipynb"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return nbformat.reads(result.stdout, as_version=4)


def _plotly_payloads(cells):
    return [
        json.dumps([payload["data"], payload["layout"]], sort_keys=True)
        for cell in cells
        for output in cell.get("outputs", ())
        if (payload := output.get("data", {}).get(PLOTLY))
    ]


def _saved(notebook):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.8":
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def _fresh():
    from hullkit._chooser_lesson import _figures

    return {key: json.loads(fig.to_json()) for key, fig in _figures().items()}


def compare(current, base, fresh):
    findings = []
    kept = _outside(current)
    if [(c.cell_type, c.source) for c in kept] != [(c.cell_type, c.source) for c in base.cells]:
        findings.append("§4.15以外のセル本文がM24基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(base):
        findings.append("§4.15以外の保存出力がM24基点と異なる")
    if _plotly_payloads(kept) != _plotly_payloads(base.cells):
        findings.append("§4.15以外の保存Plotly図がM24基点と異なる")
    kept_ids = {id(c) for c in kept}
    lesson = "\n".join(c.source for c in current.cells if id(c) not in kept_ids)
    if not lesson.startswith(START):
        findings.append("§4.15の見出しがない")
    for number in range(1, 7):
        if f"#### 4.15.{number} " not in lesson:
            findings.append(f"§4.15.{number} がない")
    saved = _saved(current)
    if set(saved) != KEYS:
        findings.append(f"§26.8保存図が不一致: {sorted(KEYS ^ set(saved))}")
    else:
        for key in sorted(KEYS):
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[key][part], sort_keys=True
                ):
                    findings.append(f"{key}.{part} が共有図と異なる")
    return findings


def negative_controls(current, base, fresh):
    rows = []
    for name in ("old prose", "new heading", "saved plot", "post heading"):
        changed = copy.deepcopy(current)
        if name == "old prose":
            next(
                c for c in changed.cells if c.source.startswith("#### 4.14.4 ")
            ).source += " altered"
        elif name == "new heading":
            cell = next(c for c in changed.cells if c.source.startswith(START))
            cell.source = cell.source.replace(START, "### 4.16 ", 1)
        elif name == "post heading":
            cell = next(c for c in changed.cells if c.source.startswith(END))
            cell.source = cell.source.replace(END, "## 6. ", 1)
        else:
            payload = next(
                output.get("data", {}).get(PLOTLY)
                for cell in changed.cells
                for output in cell.get("outputs", ())
                if output.get("data", {})
                .get(PLOTLY, {})
                .get("layout", {})
                .get("meta", {})
                .get("figure")
                == "chooser_package"
            )
            payload["data"][0]["y"][0] += 0.5
        rows.append({"mutation": name, "rejected": bool(compare(changed, base, fresh))})
    return rows


def check():
    current, base, fresh = nbformat.read(NOTEBOOK, as_version=4), _base(), _fresh()
    findings = compare(current, base, fresh)
    controls = negative_controls(current, base, fresh)
    findings.extend(
        f"negative control accepted: {row['mutation']}" for row in controls if not row["rejected"]
    )
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings, controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    findings, controls = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    current = nbformat.read(NOTEBOOK, as_version=4)
    sources = (
        "scripts/verify_chooser_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_chooser_lesson.py",
        "hullkit/src/hullkit/chooser.py",
        "hullkit/src/hullkit/bsm.py",
        "docs/validation/section-26-8/reference.json",
        "docs/validation/section-26-8/numerical-check.json",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
    )
    artifacts = ("volumes/10_exotics_martingales/exotics.ipynb",)
    record = {
        "section": "26.8",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(current.cells) - len(_outside(current)),
        "preserved_cells_outside_lesson": len(_outside(current)),
        "saved_figures": sorted(KEYS),
        "negative_controls": controls,
        "source_sha256": {
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in sources
        },
        "artifact_sha256": {
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in artifacts
        },
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.is_file() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §26.8 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §26.8 notebook, four shared figures and M24 preservation")


if __name__ == "__main__":
    main()
