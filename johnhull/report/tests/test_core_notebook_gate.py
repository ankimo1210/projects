"""Contract tests for the vol 01--17 (Hull core) notebook execution gate.

`verify_frontier_notebooks.py` covers the beyond-Hull volumes 18--28 only, so
the Hull core volumes and the two legacy notebooks had no automated execution
gate at all.  These tests pin the gate's inventory and its failure detection
without executing all nineteen notebooks (that is what `make hull-core-notebooks-check`
does).
"""

from __future__ import annotations

import nbformat
import pytest

from johnhull.scripts.verify_core_notebooks import (
    PLOTLY_MATHJAX_CDN,
    check_committed_outputs,
    core_notebooks,
    execute_notebook,
    output_notebooks,
)


def test_gate_covers_every_core_volume_and_both_legacy_notebooks():
    paths = core_notebooks()
    names = [path.name for path in paths]

    assert len(paths) == 19, names
    assert names == [
        "foundations.ipynb",
        "options_basics.ipynb",
        "greeks.ipynb",
        "futures_rates.ipynb",
        "vol_smile.ipynb",
        "numerical.ipynb",
        "swaps.ipynb",
        "risk_var.ipynb",
        "credit_xva.ipynb",
        "exotics.ipynb",
        "ir_options.ipynb",
        "qualitative_summary.ipynb",
        "stochastic_calculus.ipynb",
        "stoch_vol_fourier.ipynb",
        "advanced_numerics.ipynb",
        "xva_credit.ipynb",
        "capstone.ipynb",
        "bsm_chapter15.ipynb",
        "ir_models.ipynb",
    ]
    for path in paths:
        assert path.is_file(), path


def test_gate_reports_a_raising_cell_instead_of_passing_silently(tmp_path):
    """A notebook whose assertion fails must be reported, not swallowed.

    The volumes end in a verification cell whose asserts are the numerical
    contract; a gate that ignored the error output would report PASS for a
    volume whose own checks had started failing.
    """
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("assert 1 == 2, 'verification cell failed'")]
    )
    source = tmp_path / "broken.ipynb"
    nbformat.write(notebook, source)

    errors = execute_notebook(source)

    assert errors, "a failing assert must be reported"
    assert any("AssertionError" in error for error in errors), errors


def test_gate_returns_no_errors_for_a_clean_notebook(tmp_path):
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("assert 1 + 1 == 2\nprint('ok')")]
    )
    source = tmp_path / "clean.ipynb"
    nbformat.write(notebook, source)

    assert execute_notebook(source) == []


def test_gate_surfaces_a_missing_notebook_as_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        execute_notebook(tmp_path / "absent.ipynb")


def test_output_notebooks_are_the_static_book_copies():
    names = [path.name for path in output_notebooks()]

    assert names == [
        *[path.name for path in core_notebooks()[:16]],
        "ir_models.ipynb",
    ]
    for path in output_notebooks():
        notebook = nbformat.read(path, as_version=4)
        assert any(cell.get("outputs") for cell in notebook.cells), f"{path} has no outputs"


def test_committed_outputs_carry_no_remote_mathjax():
    """Plotly's notebook renderer injects a MathJax CDN script; the book is offline."""
    tag = (
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/'
        'MathJax.js?config=TeX-AMS-MML_SVG"></script>'
    )
    assert PLOTLY_MATHJAX_CDN.sub("", f"<div>{tag}<script>x()</script></div>") == (
        "<div><script>x()</script></div>"
    )
    for path in output_notebooks():
        assert "cdnjs.cloudflare.com/ajax/libs/mathjax" not in path.read_text(encoding="utf-8"), (
            path
        )


def test_committed_outputs_carry_no_local_paths():
    """A warning printed from a library leaks the author's checkout into the book."""
    for path in output_notebooks():
        assert "/home/" not in path.read_text(encoding="utf-8"), path


def test_output_check_flags_a_notebook_whose_outputs_were_wiped(tmp_path):
    """A builder rewrites notebooks without outputs; the check must notice."""
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('figure')")])
    source = tmp_path / "wiped.ipynb"
    nbformat.write(notebook, source)

    findings = check_committed_outputs(source)

    assert any(finding.startswith("StaleOutputs") for finding in findings), findings


def _notebook_with_output(tmp_path, source_code, output):
    cell = nbformat.v4.new_code_cell(source_code)
    cell["outputs"] = [output]
    path = tmp_path / "committed.ipynb"
    nbformat.write(nbformat.v4.new_notebook(cells=[cell]), path)
    return path


def test_output_check_flags_a_stale_printed_value(tmp_path):
    """Same output type, old number: the committed copy is stale."""
    stale = nbformat.v4.new_output("stream", name="stdout", text="1\n")
    source = _notebook_with_output(tmp_path, "print(2)", stale)

    findings = check_committed_outputs(source)

    assert any(finding.startswith("StaleOutputs") for finding in findings), findings


def test_output_check_flags_a_stale_repr_value(tmp_path):
    stale = nbformat.v4.new_output("execute_result", data={"text/plain": "1"}, execution_count=1)
    source = _notebook_with_output(tmp_path, "1 + 1", stale)

    assert any(f.startswith("StaleOutputs") for f in check_committed_outputs(source))


def test_output_check_accepts_matching_text(tmp_path):
    current = nbformat.v4.new_output("stream", name="stdout", text="2\n")
    source = _notebook_with_output(tmp_path, "print(2)", current)

    assert check_committed_outputs(source) == []


def test_output_check_masks_memory_addresses_and_timing_cells(tmp_path):
    """Object reprs and wall-clock timings legitimately change between runs."""
    address = nbformat.v4.new_output(
        "execute_result",
        data={"text/plain": "<object at 0x7f00deadbeef>"},  # IPython's pretty repr
        execution_count=1,
    )
    source = _notebook_with_output(tmp_path, "object()", address)
    assert check_committed_outputs(source) == []

    warning = nbformat.v4.new_output(
        "stream",
        name="stderr",
        text="/tmp/ipykernel_1/111.py:2: UserWarning: glyph\n  warnings.warn('glyph')\n",
    )
    source = _notebook_with_output(tmp_path, "import warnings\nwarnings.warn('glyph')", warning)
    assert check_committed_outputs(source) == []

    library = nbformat.v4.new_output(
        "stream",
        name="stderr",
        text="/elsewhere/.venv/lib/python3.12/site-packages/pkg/mod.py:1: UserWarning: glyph\n",
    )
    source = _notebook_with_output(
        tmp_path,
        "import sys\n_ = sys.stderr.write("
        "'/other/.venv/lib/python3.12/site-packages/pkg/mod.py:1: UserWarning: glyph\\n')",
        library,
    )
    assert check_committed_outputs(source) == []

    timing = nbformat.v4.new_output("stream", name="stdout", text="elapsed 0.123\n")
    source = _notebook_with_output(
        tmp_path,
        "import time\nt0 = time.perf_counter()\nprint(f'elapsed {time.perf_counter() - t0:.3f}')",
        timing,
    )
    assert check_committed_outputs(source) == []
