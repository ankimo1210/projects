"""Contract tests for the vol 01--17 (Hull core) notebook execution gate.

`verify_frontier_notebooks.py` covers the beyond-Hull volumes 18--27 only, so
the Hull core volumes and the two legacy notebooks had no automated execution
gate at all.  These tests pin the gate's inventory and its failure detection
without executing all nineteen notebooks (that is what `make hull-core-notebooks-check`
does).
"""

from __future__ import annotations

import nbformat
import pytest

from johnhull.scripts.verify_core_notebooks import core_notebooks, execute_notebook


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
