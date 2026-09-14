"""Fresh-execute the Hull core notebooks (vol 01--17 and the two legacy ones).

`verify_frontier_notebooks.py` is driven by `release_manifest.json` and so
covers the beyond-Hull volumes 18--28 only.  The Hull core volumes carry the
same kind of contract -- each ends in a verification cell whose asserts pin the
numerical identities -- but nothing executed them, so a broken volume stayed
green until somebody opened it by hand.

Execution is isolated: each notebook is executed in memory with the volume
directory as the working directory, so a check run never overwrites the
committed outputs.

The Jupyter Book does not execute notebooks, so the committed copies of
`OUTPUT_NOTEBOOKS` carry executed outputs: static PNGs for the ipympl volumes
(``HULLKIT_STATIC_FIGURES=1``, see `hullkit.nbplot.enable_static_figures`) and
the ``plotly_mimetype+notebook`` renderer, which embeds plotly.js for the book's
bundled require.js.  ``--write-outputs`` regenerates them after a builder run
(builders write notebooks without outputs); the check run fails when a
committed copy's output types or deterministic text values (printed streams,
``text/plain`` reprs) no longer match a fresh execution.  Wall-clock timing
cells are compared by type only; image and Plotly payloads are not compared by
value.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import tempfile
from collections.abc import Iterator
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

# Notebooks whose committed copies carry executed outputs for the static book:
# vol 01--12 and ir_models (ipympl figures as PNG) and vol 13--16 (Plotly).
OUTPUT_NOTEBOOKS: tuple[str, ...] = (
    *(f"volumes/{slug}/{name}" for slug, name in CORE_VOLUMES[:16]),
    "interest_rate_models/ir_models.ipynb",
)
OUTPUT_ENVIRONMENT = {
    "HULLKIT_STATIC_FIGURES": "1",
    "PLOTLY_RENDERER": "plotly_mimetype+notebook",
}
# Plotly's notebook renderer hard-codes a MathJax 2 CDN <script> into every
# figure. No committed figure uses LaTeX text and the book must run offline
# (verify_release.py rejects remote runtime dependencies), so it is stripped.
PLOTLY_MATHJAX_CDN = re.compile(
    r'<script src="https://cdnjs\.cloudflare\.com/ajax/libs/mathjax/[^"]+"></script>'
)
# Text outputs compared by value between the committed copy and a fresh run.
COMPARED_TEXT_MIME: tuple[str, ...] = ("text/plain", "text/markdown", "text/latex")
# A cell whose source contains one of these measures wall-clock time (vol 06's
# CRR / FD / LSM timing table); its outputs are compared by type only.
WALL_CLOCK_MARKERS: tuple[str, ...] = ("perf_counter", "time.time(", "timeit")
HEX_ADDRESS = re.compile(r"0x[0-9a-fA-F]{6,}")
# Warnings raised from a cell name the kernel's per-process temp file
# (/tmp/ipykernel_<pid>/<hash>.py), which changes on every run.
KERNEL_CELL_FILE = re.compile(r"/tmp/ipykernel_\d+/\d+\.py")
# Library warnings name the file of the installed package, whose prefix depends
# on the checkout and its virtual environment.
SITE_PACKAGES = re.compile(r"/[^\s'\"]*/site-packages/")


def core_notebooks() -> list[Path]:
    """Every Hull core notebook this gate executes, in volume order."""
    paths = [PROJECT / "volumes" / slug / name for slug, name in CORE_VOLUMES]
    paths.extend(PROJECT / relative for relative in LEGACY_NOTEBOOKS)
    return paths


def output_notebooks() -> list[Path]:
    """Core notebooks committed with executed outputs, in volume order."""
    return [PROJECT / relative for relative in OUTPUT_NOTEBOOKS]


@contextlib.contextmanager
def _environment(values: dict[str, str]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _execute(source: Path, *, with_outputs: bool):
    import nbformat
    from nbclient import NotebookClient

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"notebook not found: {source}")
    notebook = nbformat.read(source, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=CELL_TIMEOUT_SECONDS,
        kernel_name="python3",
        allow_errors=True,
        record_timing=False,
        store_widget_state=False,
        # Stream chunks split by kernel timing; merge them so written files and
        # output signatures are deterministic.
        coalesce_streams=True,
        resources={"metadata": {"path": str(source.parent)}},
    )
    context = _environment(OUTPUT_ENVIRONMENT) if with_outputs else contextlib.nullcontext()
    with context:
        client.execute()
    return notebook


def _errors(notebook) -> list[str]:
    return [
        f"{output.get('ename', 'Error')}: {output.get('evalue', '')}".strip()
        for cell in notebook.cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]


def _text(value: object) -> str:
    return "".join(value) if isinstance(value, list) else str(value)


def _normalize_text(value: object) -> str:
    text = HEX_ADDRESS.sub("0x…", _text(value))
    text = KERNEL_CELL_FILE.sub("<cell>", text)
    text = SITE_PACKAGES.sub("<site-packages>/", text)
    return text.replace(str(ROOT), "<root>")


def _output_signature(notebook) -> list[list[tuple[str, ...]]]:
    """Per code cell, the output types, MIME keys and deterministic text values.

    Stream text, error names and values, and the ``COMPARED_TEXT_MIME`` values of
    display outputs are compared (memory addresses, the kernel's per-process
    cell file names and checkout-dependent path prefixes masked), so a committed copy
    whose printed numbers went stale fails even when the output types still
    match. Consecutive stream outputs of the same name merge into one entry,
    since how a kernel chunks printed text depends on timing. Cells that
    measure wall-clock time (``WALL_CLOCK_MARKERS`` in the source) keep a
    type-only comparison. Images and Plotly payloads are not compared by value.
    """
    signature = []
    for cell in notebook.cells:
        if cell.get("cell_type") != "code":
            continue
        timed = any(marker in _text(cell.get("source", "")) for marker in WALL_CLOCK_MARKERS)
        entries: list[tuple[str, ...]] = []
        for output in cell.get("outputs", []):
            kind = output.get("output_type", "")
            if kind == "stream":
                name = output.get("name", "")
                text = "" if timed else _normalize_text(output.get("text", ""))
                if entries and entries[-1][:2] == ("stream", name):
                    entries[-1] = ("stream", name, entries[-1][2] + text)
                else:
                    entries.append(("stream", name, text))
                continue
            if kind == "error":
                entries.append(("error", output.get("ename", ""), output.get("evalue", "")))
                continue
            data = output.get("data", {})
            values = (
                ()
                if timed
                else tuple(
                    f"{mime}={_normalize_text(data[mime])}"
                    for mime in COMPARED_TEXT_MIME
                    if mime in data
                )
            )
            entries.append((kind, *sorted(data), *values))
        signature.append(entries)
    return signature


def _first_difference(committed, fresh) -> str:
    if len(committed) != len(fresh):
        return f"code cell count {len(committed)} committed vs {len(fresh)} fresh"
    for index, (old, new) in enumerate(zip(committed, fresh, strict=True)):
        if old != new:
            return f"code cell {index}: committed {str(old)[:160]!r} vs fresh {str(new)[:160]!r}"
    return "no difference"


def execute_notebook(source: Path) -> list[str]:
    """Execute `source` in memory and return its error outputs.

    Returns a list of ``"ename: evalue"`` strings, empty when the notebook ran
    clean. The committed file is never written back. Raises FileNotFoundError
    when `source` does not exist, rather than reporting a missing notebook as a
    pass.
    """
    from nbclient.exceptions import CellExecutionError

    try:
        notebook = _execute(source, with_outputs=False)
    except CellExecutionError as exc:  # pragma: no cover - allow_errors makes this rare
        return [f"CellExecutionError: {exc}"]
    return _errors(notebook)


def check_committed_outputs(source: Path) -> list[str]:
    """Execute with the output environment and compare against the committed copy.

    Returns errors from the fresh run plus a staleness finding when the
    committed outputs differ from the fresh run's in type or in deterministic
    text (for example after a builder rewrote the notebook without outputs, or
    after a library change moved a printed number).
    """
    import nbformat

    committed = nbformat.read(Path(source), as_version=4)
    fresh = _execute(source, with_outputs=True)
    findings = _errors(fresh)
    committed_signature = _output_signature(committed)
    fresh_signature = _output_signature(fresh)
    if committed_signature != fresh_signature:
        findings.append(
            "StaleOutputs: committed outputs differ from a fresh run "
            f"({_first_difference(committed_signature, fresh_signature)}); "
            "run verify_core_notebooks.py --write-outputs"
        )
    return findings


def write_outputs(source: Path) -> list[str]:
    """Execute with the output environment and write the notebook back in place."""
    import nbformat

    notebook = _execute(source, with_outputs=True)
    errors = _errors(notebook)
    if not errors:
        for cell in notebook.cells:
            for output in cell.get("outputs", []):
                html = output.get("data", {}).get("text/html")
                if isinstance(html, str):
                    output["data"]["text/html"] = PLOTLY_MATHJAX_CDN.sub("", html)
        nbformat.write(notebook, Path(source))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-outputs",
        action="store_true",
        help="execute the output notebooks and commit-ready write them back in place",
    )
    args = parser.parse_args(argv)
    failures: list[str] = []
    if args.write_outputs:
        for source in output_notebooks():
            relative = source.relative_to(ROOT)
            errors = write_outputs(source)
            if errors:
                failures.append(f"{relative}: {errors[0]}")
                print(f"[FAIL] {relative}: {errors[0]}")
            else:
                print(f"[WROTE] {relative}")
        return 1 if failures else 0

    with_outputs = set(output_notebooks())
    for source in core_notebooks():
        relative = source.relative_to(ROOT)
        try:
            errors = (
                check_committed_outputs(source)
                if source in with_outputs
                else execute_notebook(source)
            )
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
