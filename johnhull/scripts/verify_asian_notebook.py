"""Check the vol10 notebook after the §26.13 insertion and write the M5b record.

Three separate questions: do the committed outputs match a fresh execution, do the
saved Plotly figures equal what the shared builder produces now, and were the cells
outside §4.3 preserved against the base commit.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
NOTEBOOK = "volumes/10_exotics_martingales/exotics.ipynb"
BUILDER = "volumes/10_exotics_martingales/build_exotics_notebook.py"
OUTPUT = PROJECT / "docs/validation/section-26-13/notebook-m5b-check.json"
SOURCE_PATHS = (
    NOTEBOOK,
    BUILDER,
    "hullkit/src/hullkit/_asian_lesson.py",
    "hullkit/src/hullkit/exotics.py",
    "docs/validation/section-26-13/lesson-data.json",
    "scripts/verify_asian_notebook.py",
)
PLOTLY_MIME = "application/vnd.plotly.v1+json"


def _sha256(relative):
    return hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()


def _committed(reference, relative):
    return subprocess.run(
        ["git", "show", f"{reference}:johnhull/{relative}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout


def saved_figures(notebook):
    """Every stored Plotly payload, keyed by its figure name."""
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY_MIME)
            if payload is None:
                continue
            meta = payload.get("layout", {}).get("meta") or {}
            key = meta.get("figure") if isinstance(meta, dict) else None
            if key is None:
                continue  # plotly_viz figures carry no lesson metadata
            if key in found:
                raise ValueError(f"figure stored twice: {key}")
            found[key] = payload
    return found


def compare_figures(saved):
    """Saved payloads must equal the shared builder exactly, field by field."""
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from hullkit._asian_lesson import _figures

    results = []
    for key, figure in _figures().items():
        if key not in saved:
            raise ValueError(f"the notebook does not store {key}")
        current = json.loads(figure.to_json())
        stored = json.loads(json.dumps(saved[key]))
        for field in ("data", "layout"):
            if stored[field] != current[field]:
                raise ValueError(f"{key}: saved {field} differs from the current builder")
        results.append(
            {"figure": key, "traces": len(current["data"]),
             "menu_states": len(current["layout"].get("updatemenus", [{}])[0].get("buttons", []))}
        )
    return results


def preservation(reference, notebook):
    """Cells outside §4.3 must be identical to the base commit, in the same order."""
    before = nbformat.reads(_committed(reference, NOTEBOOK), as_version=4)
    marker = "### 4.3 アジアン"
    end_marker = "### レインボー・オプション"

    def outside(book):
        keep, inside = [], False
        for cell in book.cells:
            source = "".join(cell.source)
            if source.startswith("#### 4.3") or marker in source:
                inside = True
            elif end_marker in source:
                inside = False
            elif inside and cell.cell_type == "code" and "asian" in source:
                continue
            if not inside:
                keep.append((cell.cell_type, source))
        return keep

    kept_before, kept_after = outside(before), outside(notebook)
    if kept_before != kept_after:
        for index, (old, new) in enumerate(zip(kept_before, kept_after, strict=False)):
            if old != new:
                raise ValueError(f"cell {index} outside §4.3 changed: {old[1][:60]!r}")
        raise ValueError(
            f"cell count outside §4.3 changed: {len(kept_before)} -> {len(kept_after)}"
        )
    return {
        "base_commit": reference,
        "cells_before": len(before.cells),
        "cells_after": len(notebook.cells),
        "compared_cells_outside_section": len(kept_before),
        "identical": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="cb301c33")
    options = parser.parse_args()
    sys.path.insert(0, str(PROJECT / "scripts"))
    import verify_core_notebooks

    notebook = nbformat.read(PROJECT / NOTEBOOK, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = verify_core_notebooks.check_committed_outputs(PROJECT / NOTEBOOK)
    if errors:
        raise ValueError(f"committed outputs differ from a fresh execution: {errors[0]}")
    figures = compare_figures(saved_figures(notebook))
    record = {
        "status": "PASS",
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
            "Each saved Asian payload equals hullkit._asian_lesson._figures() exactly, data and layout."
        ),
        "preservation": preservation(options.base, notebook),
        "source_sha256": {relative: _sha256(relative) for relative in SOURCE_PATHS},
        "artifact_sha256": {NOTEBOOK: _sha256(NOTEBOOK)},
    }
    OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in
                      ("status", "cells", "code_cells", "code_cells_with_outputs")}, indent=2))
    print("preservation:", record["preservation"])
    for figure in figures:
        print(" ", figure)


if __name__ == "__main__":
    main()
