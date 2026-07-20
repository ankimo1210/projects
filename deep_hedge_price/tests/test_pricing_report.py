from __future__ import annotations

import hashlib
import json
import re

import nbformat
import numpy as np

from deep_hedge_price.pricing_notebook import (
    build_pricing_notebook,
    execute_pricing_notebook,
)
from deep_hedge_price.pricing_report import REQUIRED_SECTIONS, build_pricing_report


def _evaluation():
    error = {"mae": 0.001, "rmse": 0.002, "relative_mae": 0.01, "worst_absolute_error": 0.01}
    split = {
        "neural_price": error,
        "polynomial_price": error | {"mae": 0.002},
        "greeks": {name: error for name in ("delta", "gamma", "vega", "theta", "rho")},
        "price_buckets": {"near_atm": {"n": 10, **error}},
    }
    timing = [
        {
            "batch_size": size,
            "median_ms": value,
            "stdev_ms": 0.01,
            "throughput_per_second": 1.0,
            "warmup": 3,
            "repeats": 10,
            "hardware": {},
        }
        for size, value in ((1, 0.1), (32, 0.2), (256, 0.4))
    ]
    return {
        "schema_version": 1,
        "artifact_kind": "pricing_evaluation",
        "config_fingerprint": "config123",
        "dataset_fingerprints": {
            name: f"sha256:{name}" for name in ("train", "validation", "test", "ood")
        },
        "checkpoint_epoch": 3,
        "device": "cpu",
        "splits": {"test": split, "ood": split},
        "hard_validation": {
            "arbitrage_free": False,
            "checks": [
                {
                    "name": "price_bounds",
                    "n_checked": 10,
                    "n_violations": 1,
                    "violation_rate": 0.1,
                    "max_violation": 0.01,
                    "tolerance": 1e-6,
                    "passed": False,
                }
            ],
        },
        "benchmark": {
            "conditions": {
                "batch_sizes": [1, 32, 256],
                "warmup": 3,
                "repeats": 10,
                "device": "cpu",
                "common_input_slices": True,
            },
            "analytic": timing,
            "heston_cos": timing,
            "monte_carlo": timing,
            "polynomial": timing,
            "neural": timing,
            "teacher_metadata": {
                "heston_cos": {"terms": 128},
                "monte_carlo": {"seed": 7, "paths_per_row": 512},
            },
            "neural_vs_analytic_break_even_batch": None,
        },
        "calibration": {
            "n_quotes": 2,
            "volatility_mae": 0.01,
            "repricing_mae": 0.001,
            "recovered": [0.2, 0.3],
        },
        "acceptance": {
            "price_mae_below_1e-3": False,
            "delta_mae_below_2e-3": True,
            "all_hard_checks_pass": False,
        },
    }


def test_pricing_report_is_offline_complete_and_keeps_negative_results(tmp_path):
    evaluation = tmp_path / "artifacts" / "pricing_evaluation.json"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text(json.dumps(_evaluation()), encoding="utf-8")
    history = tmp_path / "history.json"
    history.write_text(json.dumps([{"epoch": 1, "validation_price_mae": 0.01}]))
    output = build_pricing_report(
        evaluation, history_path=history, output_path=tmp_path / "report.html"
    )
    document = output.read_text(encoding="utf-8")
    assert 'src="https://cdn.plot.ly' not in document
    assert document.count('class="plotly-graph-div"') == 4
    assert "config123" in document and "Failed acceptance checks" in document
    assert "heston_cos (256 rows)" in document and "monte_carlo (256 rows)" in document
    assert "warmup / repeats" in document and "Heston/COS" in document
    assert "MC seed / paths per row" in document and "7 / 512" in document
    assert all(section in document for section in REQUIRED_SECTIONS)
    assert all(line == line.rstrip() for line in document.splitlines())


def _write_pricing_reference(workspace):
    reference_dir = workspace / "johnhull" / "volumes" / "18_ml_surrogates" / "reference"
    reference_dir.mkdir(parents=True)
    arrays = {
        "analytic_us": np.array([3.0, 4.0, 5.0]),
        "batch_size": np.array([1, 32, 256]),
        "check_names": np.array(["price_bounds", "spot_monotonicity"]),
        "delta_error": np.array([0.001, 0.002]),
        "gamma_error": np.array([0.003, 0.004]),
        "maturity": np.array([0.1, 1.0]),
        "mlp_us": np.array([20.0, 21.0, 22.0]),
        "moneyness": np.array([0.8, 1.2]),
        "neural_price": np.array([[0.01, 0.20], [0.05, 0.30]]),
        "price_error": np.array([[0.001, 0.002], [0.003, 0.004]]),
        "truth_price": np.array([[0.011, 0.202], [0.053, 0.304]]),
        "violations_constrained": np.array([0, 0]),
        "violations_unconstrained": np.array([2.0, 1.0]),
    }
    arrays_path = reference_dir / "pricing_slices.npz"
    np.savez(arrays_path, **arrays)
    payload = {
        "schema_version": 1,
        "volume": 18,
        "metrics": {
            "break_even_batch": None,
            "delta_mae": 0.001,
            "dml_improved_a_greek_without_price_degradation": True,
            "hard_violation_rate": 0.0,
            "heston_bsm_residual_mae": 0.002,
            "heston_raw_price_mae": 0.01,
            "price_mae_normalized": 0.0005,
            "split_overlap_count": 0,
            "teacher_ci_coverage_20_seeds": 0.9,
            "teacher_se_ratio_4x_paths": 0.5,
        },
        "engine_evidence": {
            "acceptance": {"all_hard_checks_pass": True},
            "dataset_split_fingerprints": {"test": "sha256:test", "ood": "sha256:ood"},
        },
        "companions": {
            arrays_path.name: hashlib.sha256(arrays_path.read_bytes()).hexdigest(),
        },
        "companion_schemas": {
            arrays_path.name: {name: {} for name in arrays},
        },
        "limitations": [
            "Synthetic accuracy is not market forecasting power.",
            "OOD is a stress diagnostic, not an acceptance claim.",
        ],
    }
    metrics_path = reference_dir / "pricing_metrics.json"
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")
    return metrics_path


def test_notebook_02_only_reads_tracked_reference_json_and_npz(tmp_path):
    project_root = tmp_path / "deep_hedge_price"
    project_root.mkdir()
    metrics = _write_pricing_reference(tmp_path)
    path = build_pricing_notebook(project_root, metrics)
    notebook = nbformat.read(path, as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells)
    assert (
        "train(" not in source and "download" not in source.lower() and "cuda" not in source.lower()
    )
    assert "pricing_metrics.json" in source and "pricing_slices.npz" in source
    assert "pricing_evaluation" not in source and "artifacts/pricing" not in source
    for heading in (
        "Split and OOD audit",
        "Hard arbitrage diagnostics",
        "Calibration and CPU break-even",
        "negative results",
    ):
        assert heading in source


def test_notebook_02_executes_in_clean_artifact_only_checkout(tmp_path):
    project_root = tmp_path / "deep_hedge_price"
    project_root.mkdir()
    metrics = _write_pricing_reference(tmp_path)

    notebook_path, html_path = execute_pricing_notebook(project_root, metrics)

    notebook = nbformat.read(notebook_path, as_version=4)
    assert html_path.is_file()
    html = html_path.read_text(encoding="utf-8")
    assert not re.search(
        r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://',
        html,
        flags=re.IGNORECASE,
    )
    assert all(
        output.get("output_type") != "error"
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.outputs
    )
