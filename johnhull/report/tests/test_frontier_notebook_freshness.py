"""Freshness contract for the committed vol 18--28 notebooks and VALIDATION files.

`make hull-notebooks-check` used to execute each notebook in /tmp and only look
for errors, so a notebook or VALIDATION.md written before its reference artifact
was regenerated stayed green while showing stale numbers (vol 21 speedup
914.29 vs 781.91, vol 27 `alloc_normal_var` 77.53 vs 68.81).  These tests pin
the comparison helpers without executing notebooks, and check every committed
VALIDATION.md against the one its metrics.json would generate.
"""

from __future__ import annotations

import json

import nbformat
import pytest

from johnhull.scripts.verify_frontier_notebooks import (
    MANIFEST_PATH,
    stale_output_cells,
    validation_drift,
)


def _notebook(*outputs_per_cell):
    cells = []
    for outputs in outputs_per_cell:
        cell = nbformat.v4.new_code_cell("pass")
        cell.outputs = [nbformat.from_dict(output) for output in outputs]
        cells.append(cell)
    return nbformat.v4.new_notebook(cells=cells)


def _stdout(text):
    return {"output_type": "stream", "name": "stdout", "text": text}


def test_stale_output_cells_reports_changed_stdout():
    committed = _notebook([_stdout("alloc_normal_var: 77.52\n")], [_stdout("ok\n")])
    executed = _notebook([_stdout("alloc_normal_var: 68.80\n")], [_stdout("ok\n")])

    assert stale_output_cells(committed, executed) == [0]


def test_stale_output_cells_compares_execute_results():
    result = {"output_type": "execute_result", "execution_count": 1, "metadata": {}}
    committed = _notebook([{**result, "data": {"text/plain": "1.0"}}])
    executed = _notebook([{**result, "data": {"text/plain": "2.0"}}])

    assert stale_output_cells(committed, executed) == [0]


def test_stale_output_cells_ignores_figures_and_stderr():
    figure = {"output_type": "display_data", "metadata": {}, "data": {"image/png": "AAAA"}}
    committed = _notebook(
        [_stdout("same\n"), figure, {"output_type": "stream", "name": "stderr", "text": "a"}]
    )
    executed = _notebook(
        [
            _stdout("same\n"),
            {**figure, "data": {"image/png": "BBBB"}},
            {"output_type": "stream", "name": "stderr", "text": "b"},
        ]
    )

    assert stale_output_cells(committed, executed) == []


def test_stale_output_cells_rejects_a_changed_cell_layout():
    with pytest.raises(ValueError, match="cell"):
        stale_output_cells(_notebook([_stdout("a")]), _notebook([_stdout("a")], []))


def test_every_committed_validation_file_matches_its_metrics():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stale = [item["number"] for item in manifest["volumes"] if validation_drift(item)]

    assert stale == []
