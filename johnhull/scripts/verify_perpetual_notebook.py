"""Verify vol10 §4.9 (Hull GE §26.2) and preserve all M18 notebook cells."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
from verify_core_notebooks import _output_signature, check_committed_outputs, write_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
RECORD = PROJECT / "docs/validation/section-26-2/notebook-check.json"
BASE = "116ace00"
START = "### 4.9 "
END = "## 5. "
PLOTLY = "application/vnd.plotly.v1+json"
KEYS = {
    "perpetual_value",
    "perpetual_boundaries",
    "perpetual_zero_dividend",
    "perpetual_convergence",
}


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


def _payloads(cells):
    result = []
    for cell in cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload:
                result.append(json.dumps([payload["data"], payload["layout"]], sort_keys=True))
    return result


def _saved(notebook):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.2":
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def _fresh():
    from hullkit._perpetual_american_lesson import _figures

    return {key: json.loads(figure.to_json()) for key, figure in _figures().items()}


def compare(current, base, fresh):
    """Report changes outside §4.9 or drift in its headings or saved figures."""
    findings = []
    kept = _outside(current)
    if [(c.cell_type, c.source) for c in kept] != [
        (c.cell_type, c.source) for c in base.cells
    ]:
        findings.append("§4.9以外のセル本文がM18基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(
        nbformat.v4.new_notebook(cells=base.cells)
    ):
        findings.append("§4.9以外の保存出力がM18基点と異なる")
    if _payloads(kept) != _payloads(base.cells):
        findings.append("§4.9以外の保存Plotly図がM18基点と異なる")
    kept_ids = {id(c) for c in kept}
    lesson_text = "\n".join(c.source for c in current.cells if id(c) not in kept_ids)
    if not lesson_text.startswith(START):
        findings.append("§4.9の見出しがない")
    for number in range(1, 7):
        if f"#### 4.9.{number} " not in lesson_text:
            findings.append(f"§4.9.{number} がない")
    saved = _saved(current)
    if set(saved) != KEYS:
        findings.append(f"§26.2保存図が不一致: {sorted(KEYS ^ set(saved))}")
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

    def previous_source(nb):
        next(c for c in nb.cells if c.source.startswith("#### 4.8.4 ")).source += " "

    def after_heading(nb):
        cell = next(c for c in nb.cells if c.source.startswith(END))
        cell.source = cell.source.replace("## 5.", "## 6.", 1)

    def new_subsection(nb):
        cell = next(c for c in nb.cells if c.source.startswith("#### 4.9.4 "))
        cell.source = cell.source.replace("#### 4.9.4 ", "#### 4.9.9 ", 1)

    def plot(nb, key):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == key:
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError(f"missing {key}")

    def unlabeled_plot(nb):
        for cell in _outside(nb):
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and "figure" not in payload["layout"].get("meta", {}):
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError("missing an unlabeled figure")

    for label, mutate in (
        ("§4.8 source changed", previous_source),
        ("§5 heading changed", after_heading),
        ("§4.9.4 heading changed", new_subsection),
        ("§26.2 saved value changed", lambda nb: plot(nb, "perpetual_value")),
        ("§26.1 saved risk changed", lambda nb: plot(nb, "packages_risk")),
        ("unlabeled saved figure changed", unlabeled_plot),
    ):
        changed = copy.deepcopy(current)
        mutate(changed)
        found = compare(changed, base, fresh)
        rows.append({"mutation": label, "rejected": bool(found), "findings": found[:2]})
    return rows


def check():
    current = nbformat.read(NOTEBOOK, as_version=4)
    base, fresh = _base(), _fresh()
    findings = compare(current, base, fresh)
    findings += [
        f"negative control accepted: {row['mutation']}"
        for row in negative_controls(current, base, fresh)
        if not row["rejected"]
    ]
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-outputs", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write_outputs:
        findings = write_outputs(NOTEBOOK)
        for finding in findings:
            print("FAIL:", finding)
        if findings:
            raise SystemExit(1)
        print("PASS: §26.2 notebook outputs written")
        return
    findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    current = nbformat.read(NOTEBOOK, as_version=4)
    controls = negative_controls(current, _base(), _fresh())
    sources = (
        "scripts/verify_perpetual_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_perpetual_american_lesson.py",
        "hullkit/src/hullkit/perpetual_american.py",
        "docs/validation/section-26-2/reference.json",
        "docs/validation/section-26-2/numerical-check.json",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
    )
    artifacts = (
        "volumes/10_exotics_martingales/exotics.ipynb",
        "book/_build/html/notebooks/10_exotics.html",
    )
    record = {
        "section": "26.2",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(current.cells) - len(_outside(current)),
        "preserved_cells_outside_lesson": len(_outside(current)),
        "saved_figures": sorted(KEYS),
        "negative_controls": controls,
        "checks": [
            "fresh execution matches committed output signature",
            "outside §4.9 source, output signature and Plotly payloads equal M18",
            "saved §26.2 Plotly values match shared figures",
        ],
        "source_sha256": {
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in sources
        },
        "artifact_sha256": {
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in artifacts
        },
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.exists() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §26.2 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §26.2 notebook, four shared figures and M18 preservation")


if __name__ == "__main__":
    main()
