"""RB-F08 teaching figures read checked saved observations without sampling."""

import importlib.util
import json
import shutil
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F08"


def _module(name):
    path = HERE / (name + ".py")
    assert path.is_file(), "RB-F08 " + name + " is not implemented"
    spec = importlib.util.spec_from_file_location("rbf08_notebook_" + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    directory = tmp_path_factory.mktemp("rbf08_notebook")
    reference = _module("build_reference")
    protocol = directory / "protocol.json"
    protocol.write_text(json.dumps(reference.fixture_protocol()))
    artifacts = directory / "artifacts"
    reference.run_reference(artifacts, protocol_path=protocol, mode="fixture")
    return artifacts


def test_notebook_has_four_figures_and_deterministic_ids(bundle, tmp_path):
    builder = _module("build_notebook")
    a = builder.build(bundle, tmp_path / "one.ipynb")
    b = builder.build(bundle, tmp_path / "two.ipynb")
    one, two = nbformat.read(a, 4), nbformat.read(b, 4)
    assert [cell.id for cell in one.cells] == [cell.id for cell in two.cells]
    figures = [cell for cell in one.cells if cell.metadata.get("rbf08_figure")]
    assert [cell.metadata["rbf08_figure"] for cell in figures] == [1, 2, 3, 4]
    text = "\n".join(cell.source for cell in one.cells)
    for term in [
        "Student",
        "BSM",
        "clipped",
        "bias",
        "sampling",
        "cold",
        "amortized",
        "seed",
        "clip",
        "元の",
        "失敗",
        "採否",
        "fixture",
        "未受入",
    ]:
        assert term in text
    assert "fresh=False" in text
    assert "nbplot.setup()" in text
    assert not any(cell.outputs for cell in one.cells if cell.cell_type == "code")


def test_checked_fixture_executes_four_png_without_financial_rng(bundle, monkeypatch, tmp_path):
    builder = _module("build_notebook")
    path = builder.build(bundle, tmp_path / "guarded.ipynb")
    notebook = nbformat.read(path, 4)
    guard = """
import numpy as np
from hullkit import _numerical_mc as old_mc, _multilevel_mc as level_mc, _rqmc_ci as rqmc

def forbidden(*args, **kwargs):
    raise AssertionError("notebook attempted financial sampling or experiment")

np.random.default_rng = forbidden
old_mc.sobol_normal_points = forbidden
old_mc.gbm_paths_from_normals = forbidden
old_mc.randomized_qmc_price = forbidden
level_mc.gbm_level_samples = forbidden
rqmc.rqmc_gbm_call = forbidden
rqmc.rqmc_gbm_call_from_seeds = forbidden
"""
    notebook.cells.insert(1, nbformat.v4.new_code_cell(guard, id="test-financial-rng-guard"))
    for cell in notebook.cells:
        if cell.metadata.get("rbf08_loader"):
            cell.source = cell.source.replace(
                "spec.loader.exec_module(loader)",
                "spec.loader.exec_module(loader)\nloader.run_reference = forbidden",
            )
    monkeypatch.setenv("JOHNHULL_MLMC_ARTIFACTS_DIR", str(bundle))
    monkeypatch.setenv("JOHNHULL_MLMC_SOURCE_DIR", str(HERE))
    executed = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(bundle)}},
    ).execute()
    figure_cells = [cell for cell in executed.cells if cell.metadata.get("rbf08_figure")]
    assert len(figure_cells) == 4
    assert all(
        sum("image/png" in output.get("data", {}) for output in cell.outputs) == 1
        for cell in figure_cells
    )
    errors = [
        output
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.outputs
        if output.output_type == "error"
    ]
    assert not errors
    stderr = "".join(
        output.text
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.outputs
        if output.output_type == "stream" and output.name == "stderr"
    )
    assert "Glyph" not in stderr
    assert not stderr
    text = "\n".join(
        str(output.get("data", {}).get("text/plain", "")) + str(output.get("text", ""))
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.outputs
    )
    assert "fixture" in text
    assert "未受入" in text
    assert "pilotなし" in text
    assert "cold" in text
    nbformat.write(executed, path)


def test_corrupt_saved_summary_is_rejected_before_drawing(bundle, tmp_path):
    directory = tmp_path / "corrupt"
    shutil.copytree(bundle, directory)
    record_path = directory / "reference.json"
    record = json.loads(record_path.read_text())
    record["budget_cells"][0]["methods"]["mlmc"]["errors"]["rmse"] += 1
    record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        _module("build_notebook").build(directory, tmp_path / "bad.ipynb")


def test_artifact_and_source_overrides_are_explicit(bundle, monkeypatch, tmp_path):
    monkeypatch.setenv("JOHNHULL_MLMC_ARTIFACTS_DIR", str(bundle))
    monkeypatch.setenv("JOHNHULL_MLMC_SOURCE_DIR", str(HERE))
    output = _module("build_notebook").build(tmp_path / "missing", tmp_path / "overridden.ipynb")
    assert output.is_file()
    monkeypatch.setenv("JOHNHULL_MLMC_SOURCE_DIR", str(tmp_path / "missing_source"))
    with pytest.raises(FileNotFoundError):
        _module("build_notebook").build(bundle)


def test_figure_labels_keep_distinct_truths_costs_and_uncertainty():
    builder = _module("build_notebook")
    assert "coupled" in builder.FIGURE_1 and "unpaired" in builder.FIGURE_1
    assert "negative" in builder.FIGURE_1 and "alpha" in builder.FIGURE_1
    assert "predicted" in builder.FIGURE_2 and "observed" in builder.FIGURE_2
    assert "sampling" in builder.FIGURE_2 and "bias" in builder.FIGURE_2
    assert "main only" in builder.FIGURE_3 and "cold" in builder.FIGURE_3
    assert "amortized" in builder.FIGURE_3 and "stock updates" in builder.FIGURE_3
    assert "BSM" in builder.FIGURE_4 and "clipped" in builder.FIGURE_4
    assert "Wilson" in builder.FIGURE_4 and "median" in builder.FIGURE_4
    assert "p95" in builder.FIGURE_4 and "degenerate" in builder.FIGURE_4
