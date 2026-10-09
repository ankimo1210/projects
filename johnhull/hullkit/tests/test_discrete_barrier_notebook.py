"""Saved-only discrete-barrier notebook: three figures and portable execution."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import nbformat
import numpy as np
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete"
IDS = [f"{mode}_s{seed}" for mode in ("price", "dml") for seed in (11, 29, 47)]
METHODS = (
    "raw_price",
    "raw_delta",
    "conditioned_price",
    "conditioned_delta",
    "naive_pw",
    "last_conditional_pw",
    "oss_price",
    "oss_delta",
)


def builder():
    path = HERE / "build_notebook.py"
    assert path.exists(), "artifact-only discrete-barrier notebook builder is missing"
    spec = importlib.util.spec_from_file_location("discrete_barrier_notebook_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures(directory, *, timed=True, safe=True, unsupported=False):
    """Clearly synthetic saved observations, never a main financial experiment."""
    x = np.array(
        [[80.0, 0.25], [100.0, 0.25], [119.0, 0.25], [80.0, 1.0], [100.0, 1.0], [119.0, 1.0]]
    )
    target = np.array(
        [[0.05, 0.017], [3.2, 0.29], [1.7, -0.42], [0.76, 0.07], [1.8, -0.001], [0.63, -0.083]]
    )
    arrays = {
        "test.inputs": x,
        "test.reference": target,
        "model_ids": np.asarray(IDS),
        "diagnostic.inputs": np.column_stack([x, np.full(len(x), 12)]),
        "diagnostic.reference": target,
        "boundary.inputs": np.array(
            [[119.9, 1.0], [119.99, 1.0], [119.999, 1.0], [120.0, 1.0], [121.0, 1.0]]
        ),
        "boundary.reference": np.array(
            [[0.55, -0.08], [0.54, -0.08], [0.539, -0.08], [0.0, np.nan], [0.0, 0.0]]
        ),
    }
    models = {}
    for index, identifier in enumerate([*IDS, "hermite"]):
        error = 0.02 + 0.003 * index if identifier != "hermite" else 0.001
        prediction = target + np.array([error, error / 10])
        arrays[f"prediction.{identifier}.test"] = prediction
        if safe:
            arrays[f"prediction.{identifier}.safe"] = prediction * 0.999
            arrays[f"routing.{identifier}.safe"] = np.full(len(x), "approximation")
        models[identifier] = {
            "budget_failure": False,
            "updates": 2,
            "requested_updates": 2,
            "test": {"price_rmse": error, "delta_rmse": error / 10},
        }
    if safe:
        arrays["prediction.oracle.safe"] = target.copy()
        arrays["routing.oracle.safe"] = np.full(len(x), "approximation")
    record = {
        "mode": "smoke",
        "protocol": {"learning": {"seeds": [11, 29, 47]}},
        "models": {key: value for key, value in models.items() if key != "hermite"},
        "interpolation": {"test": models["hermite"]["test"]},
        "diagnostic": {"cases": []},
    }
    cases, convergence = [], []
    for row, values in zip(x, target, strict=True):
        estimates = {}
        for method in METHODS:
            coordinate = 0 if method.endswith("price") else 1
            bias = 0.15 if method in ("naive_pw", "last_conditional_pw") else 0.001
            estimates[method] = {
                "mean": float(values[coordinate] + bias),
                "se": 0.003,
                "status": "biased_control" if method.endswith("pw") else "unbiased_teacher",
            }
        cases.append(
            {
                "spot": float(row[0]),
                "maturity": float(row[1]),
                "monitoring": 12,
                "methods": estimates,
            }
        )
        convergence.append(
            {
                "spot": float(row[0]),
                "maturity": float(row[1]),
                "gl_adjacent": [{"price": 1e-9, "delta": 1e-10}],
                "independent_pde_vs_gl": {"price": 0.0001, "delta": 0.00003},
                "pde_groups": {
                    "space": [{"price": 0.0004, "delta": 0.0001}],
                    "time": [{"price": 0.00004, "delta": 0.00001}],
                },
            }
        )
    pilot = {
        "mode": "smoke",
        "summary": {
            "mc": {"cases": cases},
            "convergence": convergence,
            "m1": {"max_price_difference": 1e-12, "max_delta_difference": 1e-10},
            "frequency": {"negative_controls": {}},
            "tail": {},
        },
    }
    if timed:
        measurements, costs = [], []
        for identifier in [*IDS, "hermite", "oracle"]:
            for phase in ("raw", "safe"):
                for batch in (1, 32):
                    online = (
                        0.001
                        * (
                            2.0
                            if identifier == "oracle"
                            else 0.5
                            if identifier == "hermite"
                            else 1.0
                        )
                        * batch
                    )
                    offline = (
                        0.0 if identifier == "oracle" else 0.3 if identifier == "hermite" else 1.0
                    )
                    measurements.append(
                        {
                            "method_id": identifier,
                            "phase": phase,
                            "batch_size": batch,
                            "median_s": online,
                            "p95_s": 1.5 * online,
                        }
                    )
                    statistics = {}
                    for name, multiplier in (("median", 1.0), ("p95", 1.5)):
                        statistics[name] = {
                            "surrogate_online_s_per_batch": online * multiplier,
                            "reference_online_s_per_batch": 0.002 * batch * multiplier,
                            "training_only": {
                                "offline_s": offline,
                                "break_even": {
                                    "status": "no_online_advantage"
                                    if identifier == "oracle"
                                    else "break_even",
                                    "first_integer_call": None if identifier == "oracle" else 100,
                                },
                            },
                            "deployment": {
                                "offline_s": offline,
                                "break_even": {
                                    "status": "no_online_advantage"
                                    if identifier == "oracle"
                                    else "break_even",
                                    "first_integer_call": None if identifier == "oracle" else 100,
                                },
                            },
                        }
                    costs.append(
                        {
                            "method_id": identifier,
                            "phase": phase,
                            "batch_size": batch,
                            "statistics": statistics,
                        }
                    )
                    if unsupported and phase == "safe" and batch == 32:
                        for row in (measurements[-1], costs[-1]):
                            row["comparison_status"] = "unsupported"
                            row["unsupported_reasons"] = ["delta_undefined"]
                        for scenario in statistics.values():
                            scenario["training_only"] = None
                            scenario["deployment"] = None
        record["benchmark"] = {"measurements": measurements}
        record["costs"] = {"comparisons": costs, "loading": {"status": "measured"}}
    (directory / "reference.json").write_text(json.dumps(record))
    (directory / "pilot.json").write_text(json.dumps(pilot))
    np.savez_compressed(directory / "reference.npz", **arrays)
    # The notebook must never open this heavyweight pilot provenance archive.
    (directory / "pilot.npz").write_bytes(b"must not be opened")


def test_builder_writes_three_figures_with_no_machine_specific_paths(tmp_path):
    fixtures(tmp_path)
    path = builder().build(tmp_path)
    assert path == tmp_path / "discrete_barrier_dml.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    assert len([cell for cell in notebook.cells if "figure" in cell.metadata.get("tags", [])]) == 3
    assert str(tmp_path) not in path.read_text()


def guarded_execute(directory, *, timed=True, safe=True, unsupported=False):
    fixtures(directory, timed=timed, safe=safe, unsupported=unsupported)
    path = builder().build(directory)
    notebook = nbformat.read(path, as_version=4)
    notebook.cells.insert(
        0,
        nbformat.v4.new_code_cell(r"""import builtins
_original_import = builtins.__import__
def _saved_only_import(name, *args, **kwargs):
    if name.split(".")[0] in {"torch", "hullkit", "deep_hedge_price"}:
        raise AssertionError("No financial teacher or trainer may be imported: " + name)
    return _original_import(name, *args, **kwargs)
builtins.__import__ = _saved_only_import
import socket, urllib.request
def _offline_only(*args, **kwargs):
    raise AssertionError("Saved-artifact notebook must not use the network")
socket.create_connection = _offline_only
urllib.request.urlopen = _offline_only
import numpy as np
_saved_load = np.load
def _compact_only(file, *args, **kwargs):
    if str(file).endswith("pilot.npz"):
        raise AssertionError("Pilot raw path samples must not be loaded")
    return _saved_load(file, *args, **kwargs)
np.load = _compact_only
"""),
    )
    environment = dict(os.environ)
    environment["MPLBACKEND"] = "Agg"
    NotebookClient(
        notebook,
        timeout=90,
        kernel_name="python3",
        resources={"metadata": {"path": str(directory)}},
    ).execute(env=environment)
    nbformat.write(notebook, directory / "executed_fixture.ipynb")
    outputs = [output for cell in notebook.cells for output in cell.get("outputs", [])]
    assert not [output for output in outputs if output.get("output_type") == "error"]
    png = [output.data["image/png"] for output in outputs if "image/png" in output.get("data", {})]
    assert len(png) == 3 and all(len(value) > 1000 for value in png)
    text = "\n".join(
        str(output.get("data", {}).get("text/plain", output.get("text", ""))) for output in outputs
    )
    assert str(directory) not in text
    return text, png


def test_three_pngs_use_saved_summaries_and_all_seeds_without_teacher_or_pilot_raw(tmp_path):
    text, _ = guarded_execute(tmp_path)
    assert "SMOKE" in text and "Hermite" in text
    assert "6 SE" in text and "full batch" in text
    assert "Delta undefined" in text


def test_missing_timing_and_safe_accuracy_are_explicitly_unmeasured(tmp_path):
    text, _ = guarded_execute(tmp_path, timed=False, safe=False)
    assert "Not measured" in text
    timed = tmp_path / "timed"
    timed.mkdir()
    text, _ = guarded_execute(timed, timed=True, safe=False)
    assert "Safe accuracy not saved" in text


def test_undefined_boundary_retains_latency_without_successful_safe_cost_claim(tmp_path):
    text, _ = guarded_execute(tmp_path, unsupported=True)
    assert "Latency retained" in text
    assert "no cost recovery comparison" in text
    assert "delta_undefined" in text


def test_execute_api_with_external_artifacts_is_portable_and_overrides_agg(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    fixtures(artifacts)
    output = tmp_path / "display.ipynb"
    result = builder().build(artifacts, output, execute=True)
    assert result == output
    notebook = nbformat.read(output, as_version=4)
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
