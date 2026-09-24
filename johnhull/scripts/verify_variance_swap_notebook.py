"""Check the vol10 notebook after the §26.16 rewrite and write the M8 record.

Three separate questions: do the committed outputs match a fresh execution, do the
saved Plotly figures equal what the shared builder produces now, and were the cells
outside the new §4.6 span preserved against the base commit (with the old
variance-swap code cell, which the assertion cell still reads, kept verbatim).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = "volumes/10_exotics_martingales/exotics.ipynb"
BUILDER = "volumes/10_exotics_martingales/build_exotics_notebook.py"
OUTPUT = PROJECT / "docs/validation/section-26-16/notebook-m8-check.json"
SOURCE_PATHS = (
    NOTEBOOK,
    BUILDER,
    "hullkit/src/hullkit/_variance_swap_lesson.py",
    "hullkit/src/hullkit/variance_swaps.py",
    "docs/validation/section-26-16/lesson-data.json",
    "scripts/verify_variance_swap_notebook.py",
)
PLOTLY_MIME = "application/vnd.plotly.v1+json"
# The base notebook had one uncommented variance-swap code cell after §4.5; the new
# §4.6 span replaces it and ends where Ch.28 starts. That old cell is kept verbatim.
START_MARKERS = ("### 4.6 ボラティリティ", "# --- バリアンス・スワップ:")
END_MARKER = "## 5. マルチンゲールと測度"
RETAINED_MARKER = "# --- バリアンス・スワップ:"


def _sha256(relative):
    return hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()


def _committed(reference, relative):
    return subprocess.run(
        ["git", "show", f"{reference}:johnhull/{relative}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def saved_figures(notebook):
    """Every Plotly payload the notebook stores for a §26.16 figure."""
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY_MIME)
            if not payload:
                continue
            key = payload.get("layout", {}).get("meta", {}).get("figure")
            section = payload.get("layout", {}).get("meta", {}).get("section")
            if section == "26.16":
                found[key] = payload
    return found


def compare_figures(saved):
    """Each saved payload must equal what the shared builder produces now."""
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from hullkit._variance_swap_lesson import _figures

    built = _figures()
    if set(saved) != set(built):
        raise ValueError(f"saved figures {sorted(saved)} != built {sorted(built)}")
    lines = []
    for key, payload in sorted(saved.items()):
        fresh = json.loads(built[key].to_json())
        for part in ("data", "layout"):
            if json.dumps(payload[part], sort_keys=True) != json.dumps(fresh[part], sort_keys=True):
                raise ValueError(f"saved {key}.{part} differs from the builder")
        lines.append(f"{key}: data and layout identical ({len(payload['data'])} traces)")
    return lines


ACCEPTED_SECTIONS = ("26.10", "26.11", "26.12", "26.13", "26.14", "26.15")


def _payloads(notebook, sections):
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY_MIME)
            meta = (payload or {}).get("layout", {}).get("meta", {}) or {}
            if payload and meta.get("section") in sections:
                found[(meta["section"], meta.get("figure"))] = payload
    return found


def accepted_figures_unchanged(reference, notebook):
    """Saved Plotly payloads of the already accepted sections equal the base notebook's."""
    before = nbformat.reads(_committed(reference, NOTEBOOK), as_version=4)
    old, new = _payloads(before, ACCEPTED_SECTIONS), _payloads(notebook, ACCEPTED_SECTIONS)
    if set(old) != set(new):
        raise ValueError(f"accepted figure set changed: {sorted(set(old) ^ set(new))}")
    for key, payload in old.items():
        for part in ("data", "layout"):
            if json.dumps(payload[part], sort_keys=True) != json.dumps(
                new[key][part], sort_keys=True
            ):
                raise ValueError(f"saved {key}.{part} differs from the base notebook")
    return {
        "base_commit": reference,
        "sections": list(ACCEPTED_SECTIONS),
        "figures_compared": len(old),
        "identical": True,
    }


def preservation(reference, notebook):
    """Cells outside the rewritten §4.6 span must be identical to the base commit."""
    before = nbformat.reads(_committed(reference, NOTEBOOK), as_version=4)

    def outside(book):
        keep, inside = [], False
        for cell in book.cells:
            source = "".join(cell.source)
            if source.startswith(START_MARKERS):
                inside = True
            elif source.startswith(END_MARKER):
                inside = False
            if not inside:
                keep.append((cell.cell_type, source))
        return keep

    def retained(book):
        return [
            "".join(cell.source)
            for cell in book.cells
            if cell.cell_type == "code" and "".join(cell.source).startswith(RETAINED_MARKER)
        ]

    kept_before, kept_after = outside(before), outside(notebook)
    if kept_before != kept_after:
        for index, (old, new) in enumerate(zip(kept_before, kept_after, strict=False)):
            if old != new:
                raise ValueError(f"cell {index} outside §4.6 changed: {old[1][:60]!r}")
        raise ValueError(
            f"cell count outside §4.6 changed: {len(kept_before)} -> {len(kept_after)}"
        )
    old_cell, new_cell = retained(before), retained(notebook)
    if len(old_cell) != 1 or old_cell != new_cell:
        raise ValueError("the variance-swap code cell read by the assertion cell changed")
    return {
        "base_commit": reference,
        "cells_before": len(before.cells),
        "cells_after": len(notebook.cells),
        "compared_cells_outside_section": len(kept_before),
        "retained_variance_swap_code_cell": True,
        "identical": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="f6a2b62e")
    options = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    import verify_core_notebooks

    # Kernel working directories differ; pin this checkout with absolute paths.
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT / "hullkit/src"), str(PROJECT / "scripts"), os.environ.get("PYTHONPATH", "")]
    )
    notebook = nbformat.read(PROJECT / NOTEBOOK, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = verify_core_notebooks.check_committed_outputs(PROJECT / NOTEBOOK)
    if errors:
        raise ValueError(f"committed outputs differ from a fresh execution: {errors[0]}")
    figures = compare_figures(saved_figures(notebook))
    record = {
        "status": "PASS",
        "command": "PYTHONPATH=hullkit/src:scripts python scripts/verify_variance_swap_notebook.py --base f6a2b62e",
        "checked_at": datetime.now(UTC).isoformat(),
        "cells": len(notebook.cells),
        "code_cells": len(code_cells),
        "code_cells_with_outputs": sum(1 for cell in code_cells if cell.get("outputs")),
        "output_comparison": (
            "Separate fresh execution: output types, MIME keys and normalized deterministic text. "
            "Timing cells type-only; images and Plotly payloads excluded from that comparison."
        ),
        "saved_plotly_comparison": figures,
        "saved_plotly_note": (
            "Each saved §26.16 payload equals hullkit._variance_swap_lesson._figures() exactly, "
            "data and layout."
        ),
        "preservation": preservation(options.base, notebook),
        "accepted_section_figures": accepted_figures_unchanged(options.base, notebook),
        "source_sha256": {relative: _sha256(relative) for relative in SOURCE_PATHS},
        "artifact_sha256": {NOTEBOOK: _sha256(NOTEBOOK)},
    }
    OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: record[k] for k in ("status", "cells", "code_cells", "code_cells_with_outputs")},
            indent=2,
        )
    )
    print("preservation:", record["preservation"])
    print("accepted section figures:", record["accepted_section_figures"])
    for figure in figures:
        print(" ", figure)


if __name__ == "__main__":
    main()
