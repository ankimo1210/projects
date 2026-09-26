"""Fresh-check vol06 §27.2 outputs and preserve every cell outside lesson 8.

Lesson 8 (§27.2) was inserted between lesson 7 (§27.1) and Longstaff-Schwartz,
so exactly two headings outside the lesson are renumbered: LSM 8→9 and the
exercises 9→10 (``RENUMBERED``). All other cells must keep their source and
deterministic output signature from the base commit, and the saved §27.1 and
§27.2 Plotly payloads must equal the shared lesson figures exactly.
"""

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
NOTEBOOK = PROJECT / "volumes/06_numerical_methods/numerical.ipynb"
RECORD = PROJECT / "docs/validation/section-27-2/notebook-check.json"
BASE = "c3dd6ae5"
START = "## 8. 確率ボラティリティ・モデル（§27.2）"
END = "## 9. Longstaff-Schwartz"
RENUMBERED = {
    "## 8. Longstaff-Schwartz（LSM）": "## 9. Longstaff-Schwartz（LSM）",
    "## 9. 練習問題": "## 10. 練習問題",
}
KEYS = {"stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"}
EARLIER = {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"}
PLOTLY = "application/vnd.plotly.v1+json"


def _outside_lesson(notebook):
    cells, skipping = [], False
    for cell in notebook.cells:
        if cell.cell_type == "markdown" and cell.source.startswith(START):
            skipping = True
        if skipping and cell.cell_type == "markdown" and cell.source.startswith(END):
            skipping = False
        if not skipping:
            cells.append(cell)
    return cells


def _lesson(notebook):
    outside = {id(cell) for cell in _outside_lesson(notebook)}
    return [cell for cell in notebook.cells if id(cell) not in outside]


def _renumbered(cells):
    renamed = []
    for cell in cells:
        cell = copy.deepcopy(cell)
        for old, new in RENUMBERED.items():
            if cell.cell_type == "markdown" and cell.source.startswith(old):
                cell.source = new + cell.source[len(old) :]
        renamed.append(cell)
    return renamed


def _saved(notebook, section):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload.get("layout", {}).get("meta", {}).get("section") == section:
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def _base_notebook():
    text = subprocess.run(
        ["git", "show", f"{BASE}:johnhull/volumes/06_numerical_methods/numerical.ipynb"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return nbformat.reads(text, as_version=4)


def _fresh_figures():
    from hullkit._alternative_models_lesson import _figures as earlier
    from hullkit._stochastic_volatility_lesson import _figures as current

    return {
        "27.1": {key: json.loads(fig.to_json()) for key, fig in earlier().items()},
        "27.2": {key: json.loads(fig.to_json()) for key, fig in current().items()},
    }


def compare(current, base, fresh):
    """Static comparison of a notebook against the base and fresh shared figures."""
    findings = []
    retained, old = _outside_lesson(current), _renumbered(base.cells)
    if [(c.cell_type, c.source) for c in retained] != [(c.cell_type, c.source) for c in old]:
        findings.append("§8以外のセル本文が基点（見出しの番号変更2件を除く）と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=retained)) != _output_signature(
        nbformat.v4.new_notebook(cells=old)
    ):
        findings.append("§8以外の保存出力が基点と異なる")
    lesson_text = "\n".join(cell.source for cell in _lesson(current))
    for title in ("### 8.1 ", "### 8.2 ", "### 8.3 ", "### 8.4 ", "### 8.5 ", "### 8.6 "):
        if title not in lesson_text:
            findings.append(f"§8の小節がない: {title.strip()}")
    for section, keys in (("27.1", EARLIER), ("27.2", KEYS)):
        saved = _saved(current, section)
        if set(saved) != keys:
            findings.append(f"§{section}の保存図が不一致: {sorted(keys ^ set(saved))}")
            continue
        for key in sorted(keys):
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[section][key][part], sort_keys=True
                ):
                    findings.append(f"{key}.{part} が共有図と異なる")
    return findings


def negative_controls(current, base, fresh):
    """Mutations that ``compare`` must reject; returns one row per mutation."""
    rows = []

    def mutate_seven_source(notebook):
        cell = next(c for c in notebook.cells if c.source.startswith("### 7.1 CEV"))
        cell.source += " "

    def mutate_saved_sabr(notebook):
        for cell in notebook.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == "stochvol_sabr":
                    payload["data"][0]["y"][0] += 0.5

    def mutate_extra_heading(notebook):
        cell = next(c for c in notebook.cells if c.source.startswith("## まとめ"))
        cell.source = cell.source.replace("## まとめ", "## 11. まとめ", 1)

    def mutate_saved_cev(notebook):
        for cell in notebook.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == "alternative_cev":
                    payload["data"][0]["y"][0] += 0.5

    for name, mutation in (
        ("§7.1 source edited", mutate_seven_source),
        ("§27.2 SABR saved value changed", mutate_saved_sabr),
        ("unlisted heading renumbered", mutate_extra_heading),
        ("§27.1 CEV saved value changed", mutate_saved_cev),
    ):
        altered = copy.deepcopy(current)
        mutation(altered)
        findings = compare(altered, base, fresh)
        rows.append({"mutation": name, "rejected": bool(findings), "findings": findings[:2]})
    return rows


def check():
    """Return findings from the static comparison, the controls and a fresh run."""
    current = nbformat.read(NOTEBOOK, as_version=4)
    base, fresh = _base_notebook(), _fresh_figures()
    findings = compare(current, base, fresh)
    for row in negative_controls(current, base, fresh):
        if not row["rejected"]:
            findings.append(f"negative control accepted: {row['mutation']}")
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-outputs", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    findings = write_outputs(NOTEBOOK) if args.write_outputs else check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    if args.write_outputs:
        print("PASS: §27.2 outputs rewritten")
        return
    current = nbformat.read(NOTEBOOK, as_version=4)
    controls = negative_controls(current, _base_notebook(), _fresh_figures())
    sources = (
        "scripts/verify_stochastic_volatility_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_stochastic_volatility_lesson.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "docs/validation/section-27-2/reference.json",
        "docs/validation/section-27-1/reference.json",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
    )
    artifacts = (
        "volumes/06_numerical_methods/numerical.ipynb",
        "book/_build/html/notebooks/06_numerical.html",
    )
    record = {
        "section": "27.2",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(_lesson(current)),
        "preserved_cells_outside_lesson": len(_outside_lesson(current)),
        "renumbered_headings": RENUMBERED,
        "saved_figures": {"27.1": sorted(EARLIER), "27.2": sorted(KEYS)},
        "checks": [
            "fresh execution matches the committed output signature",
            "cells outside §8 keep base source and output signature (two listed renumberings)",
            "saved §27.1 and §27.2 Plotly data/layout equal the shared figures",
        ],
        "negative_controls": controls,
        "source_sha256": {file: _digest(PROJECT / file) for file in sources},
        "artifact_sha256": {file: _digest(PROJECT / file) for file in artifacts},
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.is_file() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.2 notebook record stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §27.2 fresh notebook, saved figures, preserved cells, negative controls")


if __name__ == "__main__":
    main()
