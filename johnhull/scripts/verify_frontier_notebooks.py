"""Fresh-execute vol 18--27 notebooks into a temporary directory."""

from __future__ import annotations

import json
import os
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


def main() -> int:
    import nbformat
    from nbclient import NotebookClient

    manifest = json.loads((PROJECT / "release_manifest.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="johnhull-notebooks-", dir="/tmp") as temporary:
        output = Path(temporary)
        for item in manifest["volumes"]:
            volume = PROJECT / "volumes" / item["slug"]
            source = volume / item["notebook"]
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
            print(f"[PASS] vol {item['number']}: {source.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
