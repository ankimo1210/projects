"""Fresh-execute vol 18--28 notebooks into a temporary directory.

Execution alone only proves that the committed notebooks still run.  It does not
prove that what they show is current: a reference artifact regenerated without
rebuilding its notebook leaves stale printed numbers in the committed outputs
(and in the Jupyter Book, which renders those outputs as they are).  The gate
therefore also compares the text a reader sees -- stdout streams and
``text/plain`` results, cell by cell -- between the committed notebook and the
fresh execution, and regenerates each volume's VALIDATION.md from its committed
metrics.json.  Figures and stderr are not compared: their bytes depend on the
plotting backend and on the local environment rather than on the artifact.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

JUPYTER_RUNTIME = Path("/tmp/johnhull-jupyter-runtime")
JUPYTER_RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
JUPYTER_RUNTIME.chmod(0o700)
os.environ["JUPYTER_RUNTIME_DIR"] = str(JUPYTER_RUNTIME)
os.environ["TMPDIR"] = "/tmp"
tempfile.tempdir = "/tmp"

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "johnhull"
MANIFEST_PATH = PROJECT / "release_manifest.json"


def _joined(text: str | list[str]) -> str:
    return "".join(text) if isinstance(text, list) else text


def _reader_text(cell) -> str:
    parts: list[str] = []
    for output in cell.get("outputs", []):
        kind = output.get("output_type")
        if kind == "stream" and output.get("name") == "stdout":
            parts.append(_joined(output.get("text", "")))
        elif kind == "execute_result":
            parts.append(_joined(output.get("data", {}).get("text/plain", "")))
    return "".join(parts)


def stale_output_cells(committed, executed) -> list[int]:
    """Indices of code cells whose stdout / text results differ after a fresh run."""

    if len(committed.cells) != len(executed.cells):
        raise ValueError(
            f"cell count differs: committed {len(committed.cells)}, executed {len(executed.cells)}"
        )
    stale: list[int] = []
    for index, (left, right) in enumerate(zip(committed.cells, executed.cells, strict=True)):
        if left.get("cell_type") != right.get("cell_type"):
            raise ValueError(f"cell {index} changed type")
        if left.get("cell_type") == "code" and _reader_text(left) != _reader_text(right):
            stale.append(index)
    return stale


def validation_drift(item: dict) -> str | None:
    """Return a reason when the committed VALIDATION.md is not what metrics.json generates."""

    scripts = str(Path(__file__).resolve().parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from build_frontier_notebooks import VOLUME_META, _validation_markdown

    volume = PROJECT / "volumes" / item["slug"]
    json_name = next(ref for ref in item["references"] if ref.endswith(".json"))
    metrics = json.loads((volume / json_name).read_text(encoding="utf-8"))
    expected = _validation_markdown(item, VOLUME_META[item["number"]], metrics)
    committed = (volume / item["validation"]).read_text(encoding="utf-8")
    if committed != expected:
        return f"{item['validation']} differs from the one generated from {json_name}"
    return None


def main() -> int:
    import nbformat
    from nbclient import NotebookClient

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="johnhull-notebooks-", dir="/tmp") as temporary:
        output = Path(temporary)
        for item in manifest["volumes"]:
            volume = PROJECT / "volumes" / item["slug"]
            source = volume / item["notebook"]
            committed = nbformat.read(source, as_version=4)
            notebook = nbformat.read(source, as_version=4)
            NotebookClient(
                notebook,
                timeout=180,
                kernel_name="python3",
                resources={"metadata": {"path": str(volume)}},
            ).execute()
            target = output / item["notebook"]
            nbformat.write(notebook, target)
            errors = [
                result
                for cell in notebook.cells
                for result in cell.get("outputs", [])
                if result.get("output_type") == "error"
            ]
            if errors:
                raise RuntimeError(f"execution errors in {source}")
            stale = stale_output_cells(committed, notebook)
            drift = validation_drift(item)
            if stale:
                problems.append(
                    f"vol {item['number']}: committed outputs are stale in cells {stale}; "
                    f"rebuild with build_{item['book_name']}_notebook.py"
                )
            if drift:
                problems.append(f"vol {item['number']}: {drift}")
            status = "STALE" if stale or drift else "PASS"
            print(f"[{status}] vol {item['number']}: {source.relative_to(ROOT)}")
    if problems:
        raise RuntimeError("stale committed notebooks or VALIDATION files:\n" + "\n".join(problems))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
