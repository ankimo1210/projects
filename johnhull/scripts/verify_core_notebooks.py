"""Fresh-execute the Hull core notebooks (vol 01--17 and the two legacy ones).

`verify_frontier_notebooks.py` is driven by `release_manifest.json` and so
covers the beyond-Hull volumes 18--27 only.  The Hull core volumes carry the
same kind of contract -- each ends in a verification cell whose asserts pin the
numerical identities -- but nothing executed them, so a broken volume stayed
green until somebody opened it by hand.

Execution is isolated: each notebook runs in a temporary copy of nothing but
itself, with the volume directory as the working directory, so a run cannot
overwrite the committed outputs.  This matters for the deep-dive volumes
13--17, whose Plotly outputs are mimetype-only and are lost if the notebook is
written back in place.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

JUPYTER_RUNTIME = Path("/tmp/johnhull-jupyter-runtime")
JUPYTER_RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
JUPYTER_RUNTIME.chmod(0o700)
os.environ["JUPYTER_RUNTIME_DIR"] = str(JUPYTER_RUNTIME)
os.environ["TMPDIR"] = "/tmp"
os.environ.setdefault("MPLBACKEND", "Agg")
tempfile.tempdir = "/tmp"

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "johnhull"

# (slug, notebook filename) for the Hull core volumes, in volume order.
CORE_VOLUMES: tuple[tuple[str, str], ...] = (
    ("01_foundations", "foundations.ipynb"),
    ("02_options_basics", "options_basics.ipynb"),
    ("03_greeks", "greeks.ipynb"),
    ("04_futures_forwards_rates", "futures_rates.ipynb"),
    ("05_vol_smile_estimation", "vol_smile.ipynb"),
    ("06_numerical_methods", "numerical.ipynb"),
    ("07_swaps", "swaps.ipynb"),
    ("08_risk_var", "risk_var.ipynb"),
    ("09_credit_xva", "credit_xva.ipynb"),
    ("10_exotics_martingales", "exotics.ipynb"),
    ("11_ir_derivatives_market", "ir_options.ipynb"),
    ("12_qualitative_summary", "qualitative_summary.ipynb"),
    ("13_stochastic_calculus", "stochastic_calculus.ipynb"),
    ("14_stoch_vol_fourier", "stoch_vol_fourier.ipynb"),
    ("15_advanced_numerics", "advanced_numerics.ipynb"),
    ("16_xva_credit", "xva_credit.ipynb"),
    ("17_capstone", "capstone.ipynb"),
)

# Notebooks kept outside `volumes/` for historical reasons (see ROADMAP.md).
LEGACY_NOTEBOOKS: tuple[str, ...] = (
    "notebooks/bsm_chapter15.ipynb",
    "interest_rate_models/ir_models.ipynb",
)

CELL_TIMEOUT_SECONDS = 600


def core_notebooks() -> list[Path]:
    """Every Hull core notebook this gate executes, in volume order."""
    paths = [PROJECT / "volumes" / slug / name for slug, name in CORE_VOLUMES]
    paths.extend(PROJECT / relative for relative in LEGACY_NOTEBOOKS)
    return paths


def execute_notebook(source: Path) -> list[str]:
    """Execute `source` in a scratch copy and return its error outputs.

    Returns a list of ``"ename: evalue"`` strings, empty when the notebook ran
    clean. The committed file is never written back: the notebook object is
    read into memory and discarded, so mimetype-only Plotly outputs survive.
    Raises FileNotFoundError when `source` does not exist, rather than
    reporting a missing notebook as a pass.
    """
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"notebook not found: {source}")

    notebook = nbformat.read(source, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=CELL_TIMEOUT_SECONDS,
        kernel_name="python3",
        allow_errors=True,
        resources={"metadata": {"path": str(source.parent)}},
    )
    try:
        client.execute()
    except CellExecutionError as exc:  # pragma: no cover - allow_errors makes this rare
        return [f"CellExecutionError: {exc}"]

    return [
        f"{output.get('ename', 'Error')}: {output.get('evalue', '')}".strip()
        for cell in notebook.cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]


def main() -> int:
    failures: list[str] = []
    for source in core_notebooks():
        relative = source.relative_to(ROOT)
        try:
            errors = execute_notebook(source)
        except FileNotFoundError as exc:
            failures.append(str(exc))
            print(f"[FAIL] {relative}: missing")
            continue
        if errors:
            failures.append(f"{relative}: {errors[0]}")
            print(f"[FAIL] {relative}: {errors[0]}")
        else:
            print(f"[PASS] {relative}")

    if failures:
        print(f"\n{len(failures)} core notebook(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"\nAll {len(core_notebooks())} core notebooks executed clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
