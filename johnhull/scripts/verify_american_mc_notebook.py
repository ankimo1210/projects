"""Fresh-check vol06 §27.8 and preserve every cell outside lesson 14.

The old LSM demonstration heading becomes §15, a comparison of CRR, finite
differences and LSM, with a new introduction pinned here. Two sentences that
§14 made inaccurate are revised (the chart note on LSM's error and the summary
row on early exercise); every other cell stays as it was at M16.
"""

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
RECORD = PROJECT / "docs/validation/section-27-8/notebook-check.json"
BASE = "99792a84"
START = "## 14. モンテカルロ法とアメリカン・オプション（§27.8）"
END = "## 15. 三つの数値解法の比較"
REPLACED = "## 14. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）"
INTRODUCTION = """## 15. 三つの数値解法の比較（CRR・FD・LSM）

同じアメリカン・プットを CRR ツリー、有限差分法（Crank–Nicolson）、最小二乗法モンテカルロ（LSM、§14）で評価し、
計算時間と誤差を比べる。ここでの LSM（`hullkit.mc.price_american_lsm`）は回帰と評価に同じ経路を使う簡易版で、
§14.4 の「推定に使った経路での評価」にあたる。行使できるのは50回なので、その厳密値（バミューダン）4.2790でも
連続行使の4.2842より0.0052低い。LSM にはさらに、2次の基底による行使の判断の劣化と、1回の実行のモンテカルロ誤差が加わる。"""
RENUMBERED = {"## 15. 練習問題": "## 16. 練習問題"}
REVISED = {
    '"注: LSM はパス数で誤差が減るが分散が大きい／CRR は参照と同族でやや有利",': (
        '"注: LSM は行使日50回と2次の基底のため、パス数を増やしても誤差は0にならない（§14.5）\\n"\n'
        '         "CRR は参照と同族でやや有利",'
    ),
    "| 1/√N、早期行使は LSM 必要 |": "| 1/√N、早期行使は回帰（LSM）か境界のパラメータ化（§14） |",
}
KEYS = {"american_mc_regression", "american_mc_boundary", "american_mc_bias", "american_mc_dates"}
EARLIER = {
    "27.1": {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"},
    "27.2": {"stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"},
    "27.3": {"ivf_smile", "ivf_local", "ivf_repricing", "ivf_joint"},
    "27.4": {"cb_tree", "cb_decisions", "cb_credit", "cb_convergence"},
    "27.5": {"path_grids", "path_interpolation", "path_prices", "path_exact"},
    "27.6": {"barrier_lattice", "barrier_convergence", "barrier_errors", "barrier_near"},
    "27.7": {
        "two_asset_nodes",
        "two_asset_convergence",
        "two_asset_errors",
        "two_asset_correlation",
    },
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
    """Base cells as M17 should keep them: §15's introduction, one heading and two sentences."""
    result, revised = [], dict.fromkeys(REVISED, 0)
    for original in cells:
        cell = copy.deepcopy(original)
        if cell.cell_type == "markdown" and cell.source.startswith(REPLACED):
            cell.source = INTRODUCTION
        for old, new in RENUMBERED.items():
            if cell.cell_type == "markdown" and cell.source.startswith(old):
                cell.source = new + cell.source[len(old) :]
        for old, new in REVISED.items():
            revised[old] += cell.source.count(old)
            cell.source = cell.source.replace(old, new)
        result.append(cell)
    if any(count != 1 for count in revised.values()):
        raise ValueError(f"each revised sentence must occur once at M16: {revised}")
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
    from hullkit._american_mc_lesson import _figures as american_mc
    from hullkit._barrier_tree_lesson import _figures as barrier_tree
    from hullkit._convertible_bond_lesson import _figures as convertible
    from hullkit._local_volatility_lesson import _figures as local
    from hullkit._path_dependent_lesson import _figures as path_dependent
    from hullkit._stochastic_volatility_lesson import _figures as stochastic
    from hullkit._two_asset_tree_lesson import _figures as two_asset

    return {
        "27.1": {k: json.loads(v.to_json()) for k, v in alternative().items()},
        "27.2": {k: json.loads(v.to_json()) for k, v in stochastic().items()},
        "27.3": {k: json.loads(v.to_json()) for k, v in local().items()},
        "27.4": {k: json.loads(v.to_json()) for k, v in convertible().items()},
        "27.5": {k: json.loads(v.to_json()) for k, v in path_dependent().items()},
        "27.6": {k: json.loads(v.to_json()) for k, v in barrier_tree().items()},
        "27.7": {k: json.loads(v.to_json()) for k, v in two_asset().items()},
        "27.8": {k: json.loads(v.to_json()) for k, v in american_mc().items()},
    }


def compare(current, base, fresh):
    """Report deviations from M16 outside §14 or from today's shared figures."""
    findings = []
    kept, old = _outside(current), _renumber(base.cells)
    if [(c.cell_type, c.source) for c in kept] != [(c.cell_type, c.source) for c in old]:
        findings.append("§14以外のセル本文がM16基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(
        nbformat.v4.new_notebook(cells=old)
    ):
        findings.append("§14以外の保存出力がM16基点と異なる")
    lesson = [cell for cell in current.cells if id(cell) not in {id(c) for c in kept}]
    text = "\n".join(cell.source for cell in lesson)
    for part in range(1, 7):
        if f"### 14.{part} " not in text:
            findings.append(f"§14.{part} がない")
    for section, keys in {**EARLIER, "27.8": KEYS}.items():
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
        next(c for c in nb.cells if c.source.startswith("### 13.3 Rubinstein")).source += " "

    def introduction(nb):
        next(c for c in nb.cells if c.source.startswith(END)).source += " "

    def plot(nb, key):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == key:
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError(f"missing {key}")

    def chart_note(nb):
        next(c for c in nb.cells if "ax7.text(" in c.source).source += " "

    def heading(nb):
        cell = next(c for c in nb.cells if c.source.startswith("## まとめ"))
        cell.source = cell.source.replace("## まとめ", "## 17. まとめ", 1)

    def prior_plot(nb):
        for cell in nb.cells:
            for output in cell.get("outputs", ()):
                payload = output.get("data", {}).get(PLOTLY)
                if payload and payload["layout"].get("meta", {}).get("figure") == "two_asset_nodes":
                    payload["data"][0]["y"][0] += 0.5
                    return
        raise ValueError("missing two_asset_nodes")

    for name, mutate in (
        ("§13 source changed", source),
        ("§27.8 saved bias changed", lambda nb: plot(nb, "american_mc_bias")),
        ("§15 introduction changed", introduction),
        ("§15 chart note changed", chart_note),
        ("unlisted heading changed", heading),
        ("§27.7 saved nodes changed", prior_plot),
    ):
        altered = copy.deepcopy(current)
        mutate(altered)
        found = compare(altered, base, fresh)
        rows.append({"mutation": name, "rejected": bool(found), "findings": found[:2]})
    return rows


def check():
    """Return M16 preservation, negative-control and fresh-execution findings."""
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
        "scripts/verify_american_mc_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_american_mc_lesson.py",
        "hullkit/src/hullkit/_two_asset_tree_lesson.py",
        "hullkit/src/hullkit/_barrier_tree_lesson.py",
        "hullkit/src/hullkit/_path_dependent_lesson.py",
        "hullkit/src/hullkit/_convertible_bond_lesson.py",
        "hullkit/src/hullkit/_local_volatility_lesson.py",
        "hullkit/src/hullkit/_stochastic_volatility_lesson.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "docs/validation/section-27-8/reference.json",
        "docs/validation/section-27-7/reference.json",
        "docs/validation/section-27-6/reference.json",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
    )
    artifacts = (
        "volumes/06_numerical_methods/numerical.ipynb",
        "book/_build/html/notebooks/06_numerical.html",
    )
    record = {
        "section": "27.8",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(current.cells) - len(_outside(current)),
        "preserved_cells_outside_lesson": len(_outside(current)),
        "replaced_introduction": {"from": REPLACED, "to": INTRODUCTION.splitlines()[0]},
        "renumbered_headings": RENUMBERED,
        "saved_figures": {
            section: sorted(keys) for section, keys in {**EARLIER, "27.8": KEYS}.items()
        },
        "negative_controls": controls,
        "checks": [
            "fresh execution matches committed output signature",
            "outside §14 source/output unchanged except the §15 introduction and one heading",
            "saved §27.1–§27.8 Plotly values match shared figures",
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
            raise SystemExit("FAIL: §27.8 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §27.8 notebook, four shared figures and M16 preservation")


if __name__ == "__main__":
    main()
