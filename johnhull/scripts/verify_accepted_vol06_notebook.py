"""Check accepted vol06 lessons on the current HEAD as later lessons are added.

The M10–M13 acceptance-time verifiers intentionally pin every other cell at
their then-current baseline. This standing check instead pins each accepted
lesson to its own accepted commit, checks today's shared Plotly payloads and
freshly executes the full current notebook. It never rewrites historical
acceptance records.
"""

import argparse
import json
import subprocess
from functools import cache
from pathlib import Path

import nbformat
from verify_core_notebooks import _output_signature, check_committed_outputs

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = PROJECT / "volumes/06_numerical_methods/numerical.ipynb"
PLOTLY = "application/vnd.plotly.v1+json"
ACCEPTED = {
    "27.1": (
        7,
        "c3dd6ae5",
        {"alternative_cev", "alternative_merton", "alternative_poisson", "alternative_vg"},
    ),
    "27.2": (
        8,
        "ad365fee",
        {"stochvol_term", "stochvol_mixing", "stochvol_correlation", "stochvol_sabr"},
    ),
    "27.3": (9, "44272e45", {"ivf_smile", "ivf_local", "ivf_repricing", "ivf_joint"}),
    "27.4": (10, "ff3ada12", {"cb_tree", "cb_decisions", "cb_credit", "cb_convergence"}),
    "27.5": (
        11,
        "e4288dc0",
        {"path_grids", "path_interpolation", "path_prices", "path_exact"},
    ),
    "27.6": (
        12,
        "42076f10",
        {"barrier_lattice", "barrier_convergence", "barrier_errors", "barrier_near"},
    ),
}


def load_current():
    """Read the current saved vol06 notebook."""
    return nbformat.read(NOTEBOOK, as_version=4)


@cache
def _accepted_notebook(commit):
    result = subprocess.run(
        ["git", "show", f"{commit}:johnhull/volumes/06_numerical_methods/numerical.ipynb"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return nbformat.reads(result.stdout, as_version=4)


def _lesson(notebook, number):
    start = None
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "markdown" and cell.source.startswith(f"## {number}. "):
            start = index
            break
    if start is None:
        return []
    end = next(
        (
            index
            for index in range(start + 1, len(notebook.cells))
            if notebook.cells[index].cell_type == "markdown"
            and notebook.cells[index].source.startswith("## ")
        ),
        len(notebook.cells),
    )
    return notebook.cells[start:end]


def _saved(notebook, section):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == section:
                found[payload["layout"]["meta"]["figure"]] = payload
    return found


def _fresh(section):
    if section == "27.1":
        from hullkit._alternative_models_lesson import _figures
    elif section == "27.2":
        from hullkit._stochastic_volatility_lesson import _figures
    elif section == "27.3":
        from hullkit._local_volatility_lesson import _figures
    elif section == "27.4":
        from hullkit._convertible_bond_lesson import _figures
    elif section == "27.5":
        from hullkit._path_dependent_lesson import _figures
    else:
        from hullkit._barrier_tree_lesson import _figures
    return {key: json.loads(fig.to_json()) for key, fig in _figures().items()}


def compare(current):
    """Return drift in accepted lesson source, outputs, order or saved figures."""
    findings = []
    for section, (number, commit, keys) in ACCEPTED.items():
        actual = _lesson(current, number)
        expected = _lesson(_accepted_notebook(commit), number)
        if not actual or not expected:
            findings.append(f"§{section} lesson heading missing")
            continue
        if [(cell.cell_type, cell.source) for cell in actual] != [
            (cell.cell_type, cell.source) for cell in expected
        ]:
            findings.append(f"§{section} accepted lesson source changed")
        if _output_signature(nbformat.v4.new_notebook(cells=actual)) != _output_signature(
            nbformat.v4.new_notebook(cells=expected)
        ):
            findings.append(f"§{section} accepted lesson saved output changed")
        saved = _saved(current, section)
        if set(saved) != keys:
            findings.append(f"§{section} saved figure keys differ: {sorted(keys ^ set(saved))}")
            continue
        fresh = _fresh(section)
        for key in sorted(keys):
            for part in ("data", "layout"):
                if json.dumps(saved[key][part], sort_keys=True) != json.dumps(
                    fresh[key][part], sort_keys=True
                ):
                    findings.append(f"§{section} {key}.{part} differs from shared figure")
    return findings


def check():
    """Check accepted slices and freshly execute the full current notebook."""
    return compare(load_current()) + check_committed_outputs(NOTEBOOK)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    findings = check()
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    print("PASS: accepted vol06 §27.1–§27.6 slices, shared figures and fresh outputs")


if __name__ == "__main__":
    main()
