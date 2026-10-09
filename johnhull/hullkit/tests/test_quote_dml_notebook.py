"""Saved-artifact quote-DML notebook: three plots without pricing or learning."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import nbformat
import numpy as np
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"


def builder():
    path = HERE / "build_notebook.py"
    assert path.exists(), "artifact-only quote-DML notebook builder is missing"
    spec = importlib.util.spec_from_file_location("quote_notebook_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def display_artifacts(directory, *, timed=False):
    """Small numeric record fixture: no teacher, optimizer or pricing imports."""
    n, shock_count = 16, 5
    x = np.column_stack(
        [
            np.tile([0.03, 0.032, 0.033, 0.0345, 0.036], (n, 1)),
            np.tile(np.linspace(80.0, 120.0, 8), 2),
            np.tile(np.linspace(0.05, 5.0, 8), 2),
        ]
    )
    arrays = {
        "test_x_quote": x,
        "test_price": np.linspace(0.2, 0.8, n),
        "test_g_quote": np.ones((n, 6)),
        "test_market_id": np.repeat([0, 1], 8),
        "reference_h": np.zeros((n, 6)),
        "reference_residual": np.zeros((n, shock_count)),
        "test_B": np.tile(np.eye(6), (n, 1, 1)),
        "shock_labels": np.array(
            ["zero", "parallel_-1bp", "parallel_+1bp", "parallel_-10bp", "parallel_+10bp"]
        ),
        "cost_rate_bp": np.array([0.0, 0.1, 0.5, 1.0]),
        "cost_stock_bp": np.array([0.0, 1.0, 5.0]),
    }
    methods = [
        "q_price",
        "theta_price",
        "theta_dml",
        "theta_quote_metric",
        "q_dml",
        "ridge_price",
        "ridge_dml",
    ]
    fits, identifiers = [], []
    for size in [16, 32]:
        for method_index, method in enumerate(methods):
            for seed in [11, 29, 47] if not method.startswith("ridge") else [None]:
                identifier = f"{method}_n{size}" + ("" if seed is None else f"_s{seed}")
                identifiers.append(identifier)
                error = (0.01 + 0.002 * method_index) * (16.0 / size)
                prefix = f"pred__{identifier}__"
                arrays[prefix + "price"] = arrays["test_price"] + error
                arrays[prefix + "g_quote"] = arrays["test_g_quote"] + error
                arrays[prefix + "h"] = arrays["reference_h"] + error
                arrays[prefix + "risk_scale"] = np.ones(6)
                arrays[prefix + "residual"] = np.tile(
                    [0.0, error * 0.001, -error * 0.001, error * 0.01, -error * 0.01], (n, 1)
                )
                arrays[prefix + "cost"] = np.full((n, 4, 3), error * 0.005)
                fits.append(
                    {
                        "id": identifier,
                        "kind": "ridge" if method.startswith("ridge") else "nn",
                        "offline_s": 0.001,
                        "budget_failure": False,
                    }
                )
    arrays["model_ids"] = np.array(identifiers)
    protocol = {
        "contract": {"strike": 100.0, "sigma": 0.2, "payout": 1.0},
        "sampling": {"contracts_per_market": 8},
        "training": {"sizes": [16, 32], "seeds": [11, 29, 47], "updates": 2},
        "bootstrap": {"repeats": 20, "seed": 20261010, "confidence": 0.95},
    }
    record = {"experiment": "smoke", "protocol": protocol, "fits": fits, "complete_fits": True}
    if timed:
        record["benchmark"] = {
            "measurements": [
                {
                    "source": "exact_cached",
                    "model_id": None,
                    "cache": "prepared",
                    "batch_size": 32,
                    "operation": "price_risk",
                    "median_s": 0.00002,
                    "p95_s": 0.00003,
                },
                {
                    "source": "exact",
                    "model_id": "exact",
                    "cache": "market",
                    "batch_size": 32,
                    "operation": "price_risk",
                    "median_s": 0.0002,
                    "p95_s": 0.0003,
                },
                {
                    "source": "raw",
                    "model_id": "q_dml_n32_s11",
                    "cache": "market",
                    "batch_size": 32,
                    "operation": "price_risk",
                    "median_s": 0.0001,
                    "p95_s": 0.0002,
                },
                {
                    "source": "safe",
                    "model_id": "q_dml_n32_s11",
                    "cache": "market",
                    "batch_size": 32,
                    "operation": "price_risk",
                    "median_s": 0.0004,
                    "p95_s": 0.0005,
                },
            ]
        }
    (directory / "replay.py").write_text((HERE / "replay.py").read_text())
    (directory / "reference.json").write_text(json.dumps(record))
    np.savez_compressed(directory / "reference.npz", **arrays)


def test_builder_emits_three_tagged_artifact_only_figures(tmp_path):
    display_artifacts(tmp_path)
    path = builder().build(tmp_path)
    assert path == tmp_path / "quote_dml.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    figures = [
        cell for cell in notebook.cells if "figure" in cell.get("metadata", {}).get("tags", [])
    ]
    assert len(figures) == 3
    sources = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert "reference.json" in sources and "reference.npz" in sources
    assert "replay.metrics" in sources
    for forbidden in [
        "import torch",
        "from hullkit",
        "from deep_hedge_price",
        "fit_nn(",
        "prepare_market(",
    ]:
        assert forbidden not in sources


def execute_guarded(directory, *, timed):
    display_artifacts(directory, timed=timed)
    path = builder().build(directory)
    notebook = nbformat.read(path, as_version=4)
    guard = nbformat.v4.new_code_cell(r"""import builtins
_original_import = builtins.__import__
def _artifact_import(name, *args, _original=_original_import, **kwargs):
    if name.split(".")[0] in {"torch", "hullkit", "deep_hedge_price"}:
        raise AssertionError("Notebook must not import teachers or learners: " + name)
    return _original(name, *args, **kwargs)
builtins.__import__ = _artifact_import
import socket, urllib.request
def _offline_only(*args, **kwargs):
    raise AssertionError("Artifact-only notebook must not use the network")
socket.create_connection = _offline_only
urllib.request.urlopen = _offline_only
""")
    notebook.cells.insert(0, guard)
    NotebookClient(
        notebook,
        timeout=90,
        kernel_name="python3",
        resources={"metadata": {"path": str(directory)}},
    ).execute()
    png = [
        output.data["image/png"]
        for cell in notebook.cells
        for output in cell.get("outputs", [])
        if "image/png" in output.get("data", {})
    ]
    assert len(png) == 3 and all(len(image) > 1000 for image in png)
    text = "\n".join(
        str(output.get("data", {}).get("text/plain", output.get("text", "")))
        for cell in notebook.cells
        for output in cell.get("outputs", [])
    )
    return text


def test_saved_arrays_render_three_pngs_without_training_pricing_or_network(tmp_path):
    text = execute_guarded(tmp_path, timed=False)
    assert "Not measured" in text or "未計測" in text


def test_recorded_timing_renders_cost_chart_without_borrowing_safe_accuracy(tmp_path):
    text = execute_guarded(tmp_path, timed=True)
    assert "safe accuracy not recorded" in text


def test_cost_plot_keeps_the_strong_cached_exact_comparator_and_batch_units(tmp_path):
    text = execute_guarded(tmp_path, timed=True)
    assert "Exact / prepared" in text and "Exact / calibrated" in text
    assert "C(N_calls)" in text and "full batches" in text


def test_execute_api_supports_external_artifacts_without_saved_absolute_paths(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    artifacts = tmp_path / "inputs"
    artifacts.mkdir()
    display_artifacts(artifacts, timed=True)
    output = tmp_path / "display.ipynb"
    path = builder().build(artifacts, output, execute=True)
    assert path == output
    notebook = nbformat.read(path, as_version=4)
    sources = "\n".join(cell.source for cell in notebook.cells)
    assert str(tmp_path) not in sources
    assert "/tmp/" not in sources
    png = [
        out.data["image/png"]
        for cell in notebook.cells
        for out in cell.get("outputs", [])
        if "image/png" in out.get("data", {})
    ]
    assert len(png) == 3
