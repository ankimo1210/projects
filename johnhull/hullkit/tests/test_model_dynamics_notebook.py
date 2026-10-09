"""RB-F04 saved-only teaching notebook; fixture results are not research evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import nbformat
import numpy as np
import pytest
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parents[2] / "research/RB-F04"


def builder():
    path = HERE / "build_notebook.py"
    assert path.exists(), "artifact-only model-dynamics notebook builder is missing"
    spec = importlib.util.spec_from_file_location("model_dynamics_notebook_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def estimate(mean, se, *, supported=True):
    return {"samples": 8, "supported": supported, "mean": mean, "standard_error": se}


def fixtures(directory, *, status="pending_precision_budget", missing=False):
    """Tiny, hand specified display summaries with a deliberately unsupported tail."""
    protocol = {
        "state": "frozen",
        "main": {"seeds": [11, 29], "paths": 4, "steps": [12, 24]},
        "parameters": {"spot": 100, "rate": 0.03, "dividend_yield": 0},
        "contract": {
            "expiry": 1,
            "asian_strike": 100,
            "include_initial": False,
            "observations": [i / 12 for i in range(1, 13)],
        },
        "two_date": {
            "first": 0.5,
            "second": 1,
            "bins": [90, 110],
            "conditional_threshold": 110,
            "minimum_count": 2,
        },
        "selected_surface": "selected",
        "freeze": {"selected_surface": "selected"},
    }
    arrays = {
        "surface.times": np.array([0.1, 0.5, 1]),
        "surface.z_nodes": np.array([-2, -1, 0, 1, 2]),
        "surface.strikes": np.array(
            [[80, 90, 100, 110, 120], [70, 80, 100, 120, 130], [60, 70, 100, 130, 140]]
        ),
        "surface.local_variance": np.array(
            [
                [np.nan, 0.05, 0.04, 0.03, np.nan],
                [0.06, 0.05, 0.04, 0.03, 0.02],
                [np.nan, 0.05, 0.04, 0.03, np.nan],
            ]
        ),
        "surface.supported": np.array(
            [[False, True, True, True, False], [True] * 5, [False, True, True, True, False]]
        ),
        "surface.density": np.array(
            [
                [np.nan, 0.04, 0.05, 0.04, np.nan],
                [0.03, 0.04, 0.05, 0.04, 0.03],
                [np.nan, 0.04, 0.05, 0.04, np.nan],
            ]
        ),
        "surface.wing_boundaries": np.array([[1, 3], [0, 4], [1, 3]]),
        "reference.quotes.times": np.array([0.5, 0.5, 1, 1]),
        "reference.quotes.strikes": np.array([90, 110, 90, 110]),
        "reference.quotes.fourier": np.array([12, 3, 15, 5]),
        "reference.quotes.independent": np.array([12.001, 2.999, 15.002, 4.998]),
        "reference.holdouts.times": np.array([1 / 3, 2 / 3]),
        "reference.holdouts.strikes": np.array([95, 105]),
        "reference.holdouts.fourier": np.array([8, 6]),
        "reference.holdouts.independent": np.array([8.001, 6.002]),
        "pilot.surface_pde.selected.quote_times": np.array([0.5, 0.5, 1, 1]),
        "pilot.surface_pde.selected.quote_strikes": np.array([90, 110, 90, 110]),
        "pilot.surface_pde.selected.price": np.array([12.02, 3.01, 15.03, 5.02]),
        "pilot.surface_pde.selected.supported": np.ones(4, dtype=bool),
        # A different pilot surface must never be chosen as the selected PDE.
        "pilot.surface_pde.baseline.quote_times": np.array([0.5, 0.5, 1, 1]),
        "pilot.surface_pde.baseline.quote_strikes": np.array([90, 110, 90, 110]),
        "pilot.surface_pde.baseline.price": np.array([30, 30, 30, 30]),
        "pilot.surface_pde.baseline.supported": np.ones(4, dtype=bool),
    }
    two_date = {
        "edges": [None, 90, 110, None],
        "samples": 8,
        "failed_pairs": 0,
        "supported": True,
        "joint_counts_heston": [[0, 0, 0], [1, 3, 1], [1, 1, 1]],
        "joint_counts_local": [[0, 0, 0], [1, 1, 2], [1, 1, 2]],
        "joint_difference": [[0, 0, 0], [0, -0.25, 0.125], [0, 0, 0.125]],
        "joint_standard_error": [[0, 0, 0], [0, 0.25, 0.125], [0, 0, 0.125]],
        "conditional_counts_heston": [0, 5, 3],
        "conditional_counts_local": [0, 4, 4],
        "conditional_heston": [None, 0.2, 1 / 3],
        "conditional_local": [None, 0.5, 0.5],
        "conditional_difference": [None, 0.3, 1 / 6],
        "conditional_standard_error": [None, 0.2, 0.1],
        "conditional_supported": [False, True, True],
    }
    levels = []
    for steps, local_mean in [(12, 5.1), (24, 5.2)]:
        levels.append(
            {
                "steps": steps,
                "asian": {
                    "heston": estimate(5.0, 0.08),
                    "local": estimate(local_mean, 0.09),
                    "difference": estimate(local_mean - 5, 0.03),
                },
                "vanilla": {
                    "heston": estimate([[12.1, 3.1], [15.1, 5.1]], [[0.1] * 2] * 2),
                    "local": estimate([[12.2, 3.2], [15.2, 5.2]], [[0.12] * 2] * 2),
                    "difference": estimate([[0.1] * 2] * 2, [[0.03] * 2] * 2),
                },
                "two_date": two_date,
                "diagnostics": {
                    "heston": {"failed_paths": 0, "negative_variance_counts": 1},
                    "local": {"failed_paths": 0, "status_counts": {"wing": 2}},
                },
            }
        )
    record = {
        "mode": "fixture",
        "protocol": protocol,
        "seeds": [{"seed": 11, "metrics": {}}, {"seed": 29, "metrics": {}}],
        "combined": {
            "levels": levels,
            "step_changes": [
                {
                    "coarse": 12,
                    "fine": 24,
                    "heston_asian": estimate(0, 0.01),
                    "local_asian": estimate(0.1, 0.02),
                    "difference_asian": estimate(0.1, 0.02),
                }
            ],
        },
        "decision": {
            "status": status,
            "difference_identified": status == "difference_identified",
            "precision_checks": {"sampling_95_half_width": True}
            if status != "pending_precision_budget"
            else {},
            "empirical_identification_threshold": 0.3
            if status != "pending_precision_budget"
            else None,
            "error_components": {
                "sampling_95_half_width": 0.0588,
                "heston_step_empirical_refinement": 0,
                "local_step_empirical_refinement": 0.1,
                "pilot_surface_empirical_refinement": 0.02,
                "pde_vanilla_residual": 0.03,
            },
        },
        "pilot_summary": {"selected_surface": "selected"},
    }
    if missing:
        levels[-1]["asian"]["difference"] = estimate(None, None, supported=False)
    np.savez_compressed(directory / "reference.npz", **arrays)
    archive = directory / "reference.npz"
    record["artifact"] = {
        "bytes": archive.stat().st_size,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "arrays": {
            key: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for key, value in arrays.items()
        },
    }
    (directory / "reference.json").write_text(json.dumps(record))


def test_builder_requires_saved_bundle_before_writing(tmp_path):
    with pytest.raises(FileNotFoundError, match="reference"):
        builder().build(tmp_path)
    assert not (tmp_path / "model_dynamics.ipynb").exists()


def test_builder_is_portable_and_uses_three_stable_figure_cells(tmp_path):
    fixtures(tmp_path)
    path = builder().build(tmp_path)
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    assert len([cell for cell in notebook.cells if "figure" in cell.metadata.get("tags", [])]) == 3
    assert str(tmp_path) not in path.read_text()
    second = tmp_path / "second.ipynb"
    builder().build(tmp_path, second)
    assert nbformat.read(second, as_version=4) == notebook


def guarded_execute(directory, *, status="pending_precision_budget", missing=False):
    fixtures(directory, status=status, missing=missing)
    path = builder().build(directory)
    notebook = nbformat.read(path, as_version=4)
    notebook.cells.insert(
        0,
        nbformat.v4.new_code_cell(r"""import builtins
_original_import = builtins.__import__
def _saved_only_import(name, *args, _saved_import=_original_import, **kwargs):
    if name.split(".")[0] in {"torch", "hullkit", "deep_hedge_price", "reference_methods", "pilot"}:
        raise AssertionError("No model, PDE, Fourier, or trainer import: " + name)
    return _saved_import(name, *args, **kwargs)
builtins.__import__ = _saved_only_import
import sys
def _source_execution_guard(event, args):
    if event == "exec":
        filename = args[0].co_filename.replace("\\", "/").rsplit("/", 1)[-1]
        if filename in {"reference_methods.py", "pilot.py", "_heston_local_surface.py", "_model_dynamics.py"}:
            raise AssertionError("No dynamic model, PDE, or Fourier import: " + filename)
sys.addaudithook(_source_execution_guard)
import socket, urllib.request
def _offline_only(*args, **kwargs):
    raise AssertionError("Saved-artifact notebook must not use the network")
socket.create_connection = _offline_only
urllib.request.urlopen = _offline_only
"""),
    )
    figure_two_index = next(
        index
        for index, cell in enumerate(notebook.cells)
        if "figure-2" in cell.metadata.get("tags", [])
    )
    notebook.cells.insert(
        figure_two_index + 1,
        nbformat.v4.new_code_cell(r"""
# All bin centers, including an unsupported left tail, need room inside the axes.
for axis in axes[1]:
    left, right = axis.get_xlim()
    assert left < 0 and right > len(bin_labels) - 1
"""),
    )
    notebook.cells.append(
        nbformat.v4.new_code_cell(r"""
# Independently hand checked fixture values: selected PDE residual, masked nodes,
# and row-specific wing locations must survive the display transformation.
assert np.allclose(residual, [.019, .011, .028, .022])
assert wing_z.tolist() == [[-1, 1], [-2, 2], [-1, 1]]
assert int(supported.sum()) == 11
assert [label.get_text() for label in axes[1, 0].get_xticklabels()] == ["12 to 24"]
assert "at every integration step" not in axes[0, 0].get_title()
""")
    )
    environment = dict(os.environ)
    environment.update(
        MPLBACKEND="Agg",
        JOHNHULL_DYNAMICS_ARTIFACT_DIR=str(directory),
        JOHNHULL_DYNAMICS_SOURCE_DIR=str(HERE),
    )
    NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(directory)}},
    ).execute(env=environment)
    outputs = [output for cell in notebook.cells for output in cell.get("outputs", [])]
    assert not [output for output in outputs if output.get("output_type") == "error"]
    assert not [output for output in outputs if output.get("name") == "stderr"]
    png = [output.data["image/png"] for output in outputs if "image/png" in output.get("data", {})]
    assert len(png) == 3 and all(len(value) > 1000 for value in png)
    text = "\n".join(
        str(
            output.get("data", {}).get(
                "text/markdown", output.get("data", {}).get("text/plain", output.get("text", ""))
            )
        )
        for output in outputs
    )
    assert str(directory) not in text
    return text


def test_saved_only_execution_retains_tails_and_unsupported_regions(tmp_path):
    text = guarded_execute(tmp_path)
    assert "pending_precision_budget" in text
    assert "unsupported" in text and "[-inf, 90)" in text and "[110, +inf)" in text
    assert "heston=[0, 5, 3]" in text and "local=[0, 4, 4]" in text
    assert "paired SE" in text and "vanilla" in text
    assert "11, 29" in text
    assert "Surface unsupported / NaN nodes: 4 / 15" in text
    assert "Selected PDE: selected" in text


def test_conclusion_follows_saved_decision_and_missing_estimate(tmp_path):
    text = guarded_execute(tmp_path, status="difference_identified")
    assert "identified" in text
    missing = tmp_path / "missing"
    missing.mkdir()
    text = guarded_execute(missing, missing=True)
    assert "Asian difference: unsupported" in text
    assert "pending_precision_budget" in text


def test_execute_api_uses_external_artifacts_and_stores_frozen_protocol(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    fixtures(artifacts)
    output = tmp_path / "display.ipynb"
    assert builder().build(artifacts, output, execute=True) == output
    notebook = nbformat.read(output, as_version=4)
    assert notebook.metadata.protocol.freeze.selected_surface == "selected"
    assert (
        len(
            [
                output
                for cell in notebook.cells
                for output in cell.get("outputs", [])
                if "image/png" in output.get("data", {})
            ]
        )
        == 3
    )
    assert str(tmp_path) not in output.read_text()


def test_saved_decision_explains_precision_and_empirical_threshold(tmp_path):
    text = guarded_execute(tmp_path, status="difference_not_identified")
    assert "difference_not_identified" in text
    assert "Frozen precision checks:" in text
    assert "sampling_95_half_width" in text
    assert "Empirical identification threshold (currency): 0.3" in text
    assert "reason not saved" not in text and "判断理由は未保存" not in text
