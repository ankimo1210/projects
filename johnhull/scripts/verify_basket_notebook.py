"""Check the vol10 notebook after the §26.15 insertion and write the M7 record.

Three separate questions: do the committed outputs match a fresh execution, do the
saved Plotly figures equal what the shared builder produces now, and were the cells
outside the rewritten §4.5 span preserved against the base commit.
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
OUTPUT = PROJECT / "docs/validation/section-26-15/notebook-m7-check.json"
SOURCE_PATHS = (
    NOTEBOOK,
    BUILDER,
    "hullkit/src/hullkit/_basket_lesson.py",
    "hullkit/src/hullkit/exotics.py",
    "docs/validation/section-26-15/lesson-data.json",
    "scripts/verify_basket_notebook.py",
)
PLOTLY_MIME = "application/vnd.plotly.v1+json"
# Only section 4.5 is rewritten; the following variance-swap code stays outside.
START_MARKER = "### 4.5 レインボー"
END_MARKER = "# --- バリアンス・スワップ:"


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
    """Every Plotly payload the notebook stores for a §26.15 figure."""
    found = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            payload = output.get("data", {}).get(PLOTLY_MIME)
            if not payload:
                continue
            key = payload.get("layout", {}).get("meta", {}).get("figure")
            section = payload.get("layout", {}).get("meta", {}).get("section")
            if section == "26.15":
                found[key] = payload
    return found


def compare_figures(saved):
    """Each saved payload must equal what the shared builder produces now."""
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from hullkit._basket_lesson import _figures

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


def preservation(reference, notebook):
    """Cells outside the rewritten §4.5 span must be identical to the base commit."""
    before = nbformat.reads(_committed(reference, NOTEBOOK), as_version=4)

    def outside(book):
        keep, inside = [], False
        for cell in book.cells:
            source = "".join(cell.source)
            if source.startswith(START_MARKER):
                inside = True
            elif source.startswith(END_MARKER):
                inside = False
            if not inside:
                keep.append((cell.cell_type, source))
        return keep

    kept_before, kept_after = outside(before), outside(notebook)
    if kept_before != kept_after:
        for index, (old, new) in enumerate(zip(kept_before, kept_after, strict=False)):
            if old != new:
                raise ValueError(f"cell {index} outside §4.5 changed: {old[1][:60]!r}")
        raise ValueError(
            f"cell count outside §4.5 changed: {len(kept_before)} -> {len(kept_after)}"
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
    parser.add_argument("--base", default="9b7a75c7")
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
        "command": "PYTHONPATH=hullkit/src:scripts python scripts/verify_basket_notebook.py --base 9b7a75c7",
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
            "Each saved basket payload equals hullkit._basket_lesson._figures() exactly, "
            "data and layout."
        ),
        "preservation": preservation(options.base, notebook),
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
    for figure in figures:
        print(" ", figure)


if __name__ == "__main__":
    main()
