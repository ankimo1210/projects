"""Write or verify vol10 §4.8 (Hull §26.1 packages) and preserve every other cell.

`--write-outputs` freshly executes `exotics.ipynb` and saves its outputs.  The check
compares each cell outside §4.8 (source, output signature and every saved Plotly
payload) with the M17 commit, matches the saved §26.1 and §26.10–§26.17 figures
with today's shared figures, and re-executes the notebook.
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
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
RECORD = PROJECT / "docs/validation/section-26-1/notebook-check.json"
BASE = "811b1792"
START = "### 4.8 パッケージ（§26.1"
END = "## 5. マルチンゲールと測度"
PLOTLY = "application/vnd.plotly.v1+json"
KEYS = {"packages_strikes", "packages_range_forward", "packages_deferred", "packages_risk"}
EARLIER = {
    "26.10": {"binary_payoffs", "binary_replication", "binary_spreads", "binary_delta"},
    "26.11": {
        "lookback_payoffs",
        "lookback_history",
        "lookback_replication",
        "lookback_monitoring",
    },
    "26.12": {"shout_payoff", "shout_decision", "shout_boundary", "shout_comparison"},
    "26.13": {"asian_payoff", "asian_distribution", "asian_observations", "asian_error"},
    "26.14": {"exchange_payoff", "exchange_correlation", "exchange_rate", "exchange_american"},
    "26.15": {"basket_payoff", "basket_correlation", "basket_comparison", "basket_error"},
    "26.16": {"varswap_payoff", "varswap_strip", "varswap_replication", "volswap_convexity"},
    "26.17": {"static_boundary", "static_ladder", "static_boundary_error", "static_convergence"},
}


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


def _saved(notebook, section):
    result = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == section:
                result[payload["layout"]["meta"]["figure"]] = payload
    return result


def _fresh():
    from hullkit._asian_lesson import _figures as asian
    from hullkit._basket_lesson import _figures as basket
    from hullkit._binary_lesson import _figures as binary
    from hullkit._exchange_lesson import _figures as exchange
    from hullkit._lookback_lesson import _figures as lookback
    from hullkit._packages_lesson import _figures as packages
    from hullkit._shout_lesson import _figures as shout
    from hullkit._static_replication_lesson import _figures as static
    from hullkit._variance_swap_lesson import _figures as variance

    return {
        section: {key: json.loads(fig.to_json()) for key, fig in figures().items()}
        for section, figures in {
            "26.1": packages,
            "26.10": binary,
            "26.11": lookback,
            "26.12": shout,
            "26.13": asian,
            "26.14": exchange,
            "26.15": basket,
            "26.16": variance,
            "26.17": static,
        }.items()
    }


def compare(current, base, fresh):
    """Report deviations from M17 outside §4.8 or from today's shared figures."""
    findings = []
    kept = _outside(current)
    if [(c.cell_type, c.source) for c in kept] != [(c.cell_type, c.source) for c in base.cells]:
        findings.append("§4.8以外のセル本文がM17基点と異なる")
    if _output_signature(nbformat.v4.new_notebook(cells=kept)) != _output_signature(
        nbformat.v4.new_notebook(cells=base.cells)
    ):
        findings.append("§4.8以外の保存出力がM17基点と異なる")
    if _payloads(kept) != _payloads(base.cells):
        findings.append("§4.8以外の保存Plotly図がM17基点と異なる")
    kept_ids = {id(c) for c in kept}
    text = "\n".join(c.source for c in current.cells if id(c) not in kept_ids)
    for part in range(1, 7):
        if f"#### 4.8.{part} " not in text:
            findings.append(f"§4.8.{part} がない")
    for section, keys in {"26.1": KEYS, **EARLIER}.items():
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
    """Check rejection of prior-lesson, new-lesson and unrelated edits."""
    rows = []

    def source(nb):
        next(c for c in nb.cells if c.source.startswith("#### 4.7.3 ")).source += " "

    def heading(nb):
        cell = next(c for c in nb.cells if c.source.startswith(END))
        cell.source = cell.source.replace("## 5.", "## 6.", 1)

    def subsection(nb):
        cell = next(c for c in nb.cells if c.source.startswith("#### 4.8.4 "))
        cell.source = cell.source.replace("#### 4.8.4 ", "#### 4.8.9 ", 1)

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

    for name, mutate in (
        ("§4.7 source changed", source),
        ("§5 heading changed", heading),
        ("§4.8.4 heading changed", subsection),
        ("§26.1 saved deferred changed", lambda nb: plot(nb, "packages_deferred")),
        ("§26.17 saved boundary changed", lambda nb: plot(nb, "static_boundary")),
        ("unlabeled saved figure changed", unlabeled_plot),
    ):
        altered = copy.deepcopy(current)
        mutate(altered)
        found = compare(altered, base, fresh)
        rows.append({"mutation": name, "rejected": bool(found), "findings": found[:2]})
    return rows


def check():
    """Return M17 preservation, negative-control and fresh-execution findings."""
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
    parser.add_argument("--write-outputs", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write_outputs:
        errors = write_outputs(NOTEBOOK)
        for error in errors:
            print("FAIL:", error)
        if errors:
            raise SystemExit(1)
        print("PASS: §26.1 notebook outputs written")
        return
    findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    current = nbformat.read(NOTEBOOK, as_version=4)
    controls = negative_controls(current, _base(), _fresh())
    sources = (
        "scripts/verify_packages_notebook.py",
        "scripts/verify_core_notebooks.py",
        "hullkit/src/hullkit/_packages_lesson.py",
        "hullkit/src/hullkit/packages.py",
        "hullkit/src/hullkit/_static_replication_lesson.py",
        "hullkit/src/hullkit/_variance_swap_lesson.py",
        "hullkit/src/hullkit/_basket_lesson.py",
        "hullkit/src/hullkit/_exchange_lesson.py",
        "hullkit/src/hullkit/_asian_lesson.py",
        "hullkit/src/hullkit/_shout_lesson.py",
        "hullkit/src/hullkit/_lookback_lesson.py",
        "hullkit/src/hullkit/_binary_lesson.py",
        "docs/validation/section-26-1/reference.json",
        "docs/validation/section-26-1/numerical-check.json",
        "volumes/10_exotics_martingales/build_exotics_notebook.py",
        "volumes/10_exotics_martingales/exotics.ipynb",
    )
    artifacts = (
        "volumes/10_exotics_martingales/exotics.ipynb",
        "book/_build/html/notebooks/10_exotics.html",
    )
    record = {
        "section": "26.1",
        "status": "PASS",
        "base": BASE,
        "cells": len(current.cells),
        "lesson_cells": len(current.cells) - len(_outside(current)),
        "preserved_cells_outside_lesson": len(_outside(current)),
        "saved_figures": {
            section: sorted(keys) for section, keys in {"26.1": KEYS, **EARLIER}.items()
        },
        "negative_controls": controls,
        "checks": [
            "fresh execution matches committed output signature",
            "outside §4.8 source, output signature and Plotly payloads equal M17",
            "saved §26.1 and §26.10–§26.17 Plotly values match shared figures",
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
            raise SystemExit("FAIL: §26.1 notebook record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §26.1 notebook, four shared figures and M17 preservation")


if __name__ == "__main__":
    main()
