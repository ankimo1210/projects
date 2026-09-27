"""Fresh-check vol06 §27.3 and preserve all cells outside lesson 9."""

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
RECORD = PROJECT / "docs/validation/section-27-3/notebook-check.json"
BASE = "ad365fee"
START = "## 9. IVF（局所ボラティリティ）モデル（§27.3）"
END = "## 10. Longstaff-Schwartz"
RENUMBERED = {
    "## 9. Longstaff-Schwartz（LSM）": "## 10. Longstaff-Schwartz（LSM）",
    "## 10. 練習問題": "## 11. 練習問題",
}
KEYS = {"ivf_smile", "ivf_local", "ivf_repricing", "ivf_joint"}
EARLIER = {
    "27.1": {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"},
    "27.2": {"stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"},
}
PLOTLY = "application/vnd.plotly.v1+json"


def _outside_lesson(notebook):
    result, skipping = [], False
    for cell in notebook.cells:
        if cell.cell_type == "markdown" and cell.source.startswith(START):
            skipping = True
        if skipping and cell.cell_type == "markdown" and cell.source.startswith(END):
            skipping = False
        if not skipping:
            result.append(cell)
    return result


def _lesson(notebook):
    outside = {id(cell) for cell in _outside_lesson(notebook)}
    return [cell for cell in notebook.cells if id(cell) not in outside]


def _base_notebook():
    result = subprocess.run(
        ["git", "show", f"{BASE}:johnhull/volumes/06_numerical_methods/numerical.ipynb"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
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


def _fresh_figures():
    from hullkit._alternative_models_lesson import _figures as alternative
    from hullkit._local_volatility_lesson import _figures as local
    from hullkit._stochastic_volatility_lesson import _figures as stochastic

    return {
        "27.1": {key: json.loads(fig.to_json()) for key, fig in alternative().items()},
        "27.2": {key: json.loads(fig.to_json()) for key, fig in stochastic().items()},
        "27.3": {key: json.loads(fig.to_json()) for key, fig in local().items()},
    }


def compare(current, base, fresh):
    """Return source, output and shared-figure differences from the M11 base."""
    findings = []
    kept, old = _outside_lesson(current), _renumber(base.cells)
    if [(c.cell_type, c.source) for c in kept] != [(c.cell_type, c.source) for c in old]:
        findings.append("§9以外のセル本文が基点（見出し番号2件を除く）と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(
        nbformat.v4.new_notebook(cells=old)
    ):
        findings.append("§9以外の保存出力が基点と異なる")
    text = "\n".join(cell.source for cell in _lesson(current))
    for section in range(1, 7):
        if f"### 9.{section} " not in text:
            findings.append(f"§9.{section} がない")
    for section, keys in {**EARLIER, "27.3": KEYS}.items():
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
    """Check that source, new value, heading and earlier value mutations fail."""
    rows = []

    def change_source(nb):
        next(c for c in nb.cells if c.source.startswith("### 8.1 時間で決まるボラ")).source += " "

    def change_plot(nb, figure):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == figure:
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError(f"missing saved plot: {figure}")

    def change_heading(nb):
        cell = next(c for c in nb.cells if c.source.startswith("## まとめ"))
        cell.source = cell.source.replace("## まとめ", "## 12. まとめ", 1)

    for name, mutation in (
        ("§8.1 source changed", change_source),
        ("§27.3 saved local volatility changed", lambda nb: change_plot(nb, "ivf_local")),
        ("unlisted heading changed", change_heading),
        ("§27.2 saved SABR changed", lambda nb: change_plot(nb, "stochvol_sabr")),
    ):
        altered = copy.deepcopy(current)
        mutation(altered)
        findings = compare(altered, base, fresh)
        rows.append({"mutation": name, "rejected": bool(findings), "findings": findings[:2]})
    return rows


def check():
    """Return static, negative-control and fresh-execution findings."""
    current = nbformat.read(NOTEBOOK, as_version=4)
    base, fresh = _base_notebook(), _fresh_figures()
    findings = compare(current, base, fresh)
    findings.extend(
        f"negative control accepted: {row['mutation']}"
        for row in negative_controls(current, base, fresh)
        if not row["rejected"]
    )
    findings.extend(check_committed_outputs(NOTEBOOK))
    return findings


def sha(file):
    return hashlib.sha256((PROJECT / file).read_bytes()).hexdigest()


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
    controls = negative_controls(current, _base_notebook(), _fresh_figures())
    sources = (
        "scripts/verify_local_volatility_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_local_volatility_lesson.py",
        "hullkit/src/hullkit/_stochastic_volatility_lesson.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "docs/validation/section-27-3/reference.json",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
    )
    record = {
        "section": "27.3",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(_lesson(current)),
        "preserved_cells_outside_lesson": len(_outside_lesson(current)),
        "renumbered_headings": RENUMBERED,
        "saved_figures": {
            "27.1": sorted(EARLIER["27.1"]),
            "27.2": sorted(EARLIER["27.2"]),
            "27.3": sorted(KEYS),
        },
        "negative_controls": controls,
        "checks": [
            "fresh execution matches committed output signature",
            "outside §9 source/output unchanged except two listed headings",
            "saved §27.1–§27.3 Plotly values match shared figures",
        ],
        "source_sha256": {file: sha(file) for file in sources},
        "artifact_sha256": {
            file: sha(file)
            for file in (
                "volumes/06_numerical_methods/numerical.ipynb",
                "book/_build/html/notebooks/06_numerical.html",
            )
        },
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.is_file() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.3 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §27.3 fresh notebook, preserved cells and saved figures")


if __name__ == "__main__":
    main()
