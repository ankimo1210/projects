"""Fresh-check vol06 §27.5 and preserve every cell outside lesson 11."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import nbformat
from verify_core_notebooks import _output_signature, check_committed_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/06_numerical_methods/numerical.ipynb"
RECORD = PROJECT / "docs/validation/section-27-5/notebook-check.json"
BASE = "84387c5d"
START = "## 11. 経路依存デリバティブ（§27.5）"
END = "## 12. Longstaff-Schwartz"
RENUMBERED = {
    "## 11. Longstaff-Schwartz（LSM）": "## 12. Longstaff-Schwartz（LSM）",
    "## 12. 練習問題": "## 13. 練習問題",
}
KEYS = {"path_grids", "path_interpolation", "path_prices", "path_exact"}
EARLIER = {
    "27.1": {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"},
    "27.2": {"stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"},
    "27.3": {"ivf_smile", "ivf_local", "ivf_repricing", "ivf_joint"},
    "27.4": {"cb_tree", "cb_decisions", "cb_credit", "cb_convergence"},
}
PLOTLY = "application/vnd.plotly.v1+json"


def _outside(notebook):
    result, skipping = [], False
    for cell in notebook.cells:
        if cell.cell_type == "markdown" and cell.source.startswith(START):
            skipping = True
        if skipping and cell.cell_type == "markdown" and cell.source.startswith(END):
            skipping = False
        if not skipping:
            result.append(cell)
    return result


def _base():
    result = subprocess.run(
        ["git", "show", f"{BASE}:johnhull/volumes/06_numerical_methods/numerical.ipynb"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return nbformat.reads(result.stdout, as_version=4)


def _renumber(cells):
    result = []
    for original in cells:
        cell = copy.deepcopy(original)
        for old, new in RENUMBERED.items():
            if cell.cell_type == "markdown" and cell.source.startswith(old):
                cell.source = new + cell.source[len(old) :]
        result.append(cell)
    return result


def _saved(notebook, section):
    result = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == section:
                result[payload["layout"]["meta"]["figure"]] = payload
    return result


def _fresh():
    from hullkit._alternative_models_lesson import _figures as alternative
    from hullkit._convertible_bond_lesson import _figures as convertible
    from hullkit._local_volatility_lesson import _figures as local
    from hullkit._path_dependent_lesson import _figures as path_dependent
    from hullkit._stochastic_volatility_lesson import _figures as stochastic

    return {
        "27.1": {k: json.loads(v.to_json()) for k, v in alternative().items()},
        "27.2": {k: json.loads(v.to_json()) for k, v in stochastic().items()},
        "27.3": {k: json.loads(v.to_json()) for k, v in local().items()},
        "27.4": {k: json.loads(v.to_json()) for k, v in convertible().items()},
        "27.5": {k: json.loads(v.to_json()) for k, v in path_dependent().items()},
    }


def compare(current, base, fresh):
    """Report deviations from M13 outside §11 or from today's shared figures."""
    findings = []
    kept, old = _outside(current), _renumber(base.cells)
    if [(c.cell_type, c.source) for c in kept] != [(c.cell_type, c.source) for c in old]:
        findings.append("§11以外のセル本文がM13基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(
        nbformat.v4.new_notebook(cells=old)
    ):
        findings.append("§11以外の保存出力がM13基点と異なる")
    lesson = [cell for cell in current.cells if id(cell) not in {id(c) for c in kept}]
    text = "\n".join(cell.source for cell in lesson)
    for part in range(1, 7):
        if f"### 11.{part} " not in text:
            findings.append(f"§11.{part} がない")
    for section, keys in {**EARLIER, "27.5": KEYS}.items():
        saved = _saved(current, section)
        if set(saved) != keys:
            findings.append(f"§{section}保存図が不一致: {sorted(keys ^ set(saved))}")
            continue
        for key in sorted(keys):
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[section][key][part], sort_keys=True
                ):
                    findings.append(f"{key}.{part} が共有図と異なる")
    return findings


def negative_controls(current, base, fresh):
    """Check rejection of prior source, new/prior plot and unrelated heading edits."""
    rows = []

    def source(nb):
        next(c for c in nb.cells if c.source.startswith("### 10.1 契約")).source += " "

    def plot(nb, key):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == key:
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError(f"missing {key}")

    def heading(nb):
        cell = next(c for c in nb.cells if c.source.startswith("## まとめ"))
        cell.source = cell.source.replace("## まとめ", "## 14. まとめ", 1)

    def prior_plot(nb):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == "cb_tree":
                    payload["data"][0]["customdata"][0][0] += 0.5
                    return
        raise ValueError("missing cb_tree")

    for name, mutate in (
        ("§10 source changed", source),
        ("§27.5 saved grid changed", lambda nb: plot(nb, "path_grids")),
        ("unlisted heading changed", heading),
        ("§27.4 saved tree changed", prior_plot),
    ):
        altered = copy.deepcopy(current)
        mutate(altered)
        found = compare(altered, base, fresh)
        rows.append({"mutation": name, "rejected": bool(found), "findings": found[:2]})
    return rows


def check():
    """Return M13 preservation, negative-control and fresh-execution findings."""
    current = nbformat.read(NOTEBOOK, as_version=4)
    base, fresh = _base(), _fresh()
    findings = compare(current, base, fresh)
    findings.extend(
        f"negative control accepted: {row['mutation']}"
        for row in negative_controls(current, base, fresh)
        if not row["rejected"]
    )
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    current = nbformat.read(NOTEBOOK, as_version=4)
    controls = negative_controls(current, _base(), _fresh())
    sources = (
        "scripts/verify_path_dependent_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_path_dependent_lesson.py",
        "hullkit/src/hullkit/_convertible_bond_lesson.py",
        "hullkit/src/hullkit/_local_volatility_lesson.py",
        "hullkit/src/hullkit/_stochastic_volatility_lesson.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "docs/validation/section-27-5/reference.json",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
    )
    artifacts = (
        "volumes/06_numerical_methods/numerical.ipynb",
        "book/_build/html/notebooks/06_numerical.html",
    )
    record = {
        "section": "27.5",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(current.cells) - len(_outside(current)),
        "preserved_cells_outside_lesson": len(_outside(current)),
        "renumbered_headings": RENUMBERED,
        "saved_figures": {
            section: sorted(keys) for section, keys in {**EARLIER, "27.5": KEYS}.items()
        },
        "negative_controls": controls,
        "checks": [
            "fresh execution matches committed output signature",
            "outside §11 source/output unchanged except two listed headings",
            "saved §27.1–§27.5 Plotly values match shared figures",
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
            raise SystemExit("FAIL: §27.5 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §27.5 notebook, four shared figures and M13 preservation")


if __name__ == "__main__":
    main()
