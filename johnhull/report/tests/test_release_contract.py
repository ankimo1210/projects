from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from johnhull.scripts.frontier_acceptance import evaluate_acceptance
from johnhull.scripts.verify_release import (
    _check_notebook,
    _check_npz_schema,
    _check_reference,
    _load_json,
)


def test_npz_release_schema_checks_names_shape_dtype_units_and_finiteness(tmp_path):
    path = tmp_path / "reference.npz"
    np.savez(path, curve=np.array([0.1, 0.2], dtype=np.float64))
    schema = {
        "curve": {
            "shape": [2],
            "dtype": "float64",
            "unit": "decimal volatility",
        }
    }
    findings = []
    _check_npz_schema(path, schema, findings)
    assert findings == []

    bad_schema = {"curve": {"shape": [3], "dtype": "float32", "unit": ""}}
    findings = []
    _check_npz_schema(path, bad_schema, findings)
    assert {finding.check for finding in findings} == {"reference-schema"}
    assert {"shape mismatch", "dtype mismatch", "unit missing"} == {
        finding.detail.split(":", 1)[0] for finding in findings
    }


def test_npz_release_schema_rejects_nonfinite_numeric_values(tmp_path):
    path = tmp_path / "reference.npz"
    np.savez(path, values=np.array([1.0, np.nan]))
    findings = []
    _check_npz_schema(
        path,
        {"values": {"shape": [2], "dtype": "float64", "unit": "dimensionless"}},
        findings,
    )
    assert len(findings) == 1
    assert "non-finite" in findings[0].detail


def test_json_loader_rejects_nonfinite_constants_and_overflow(tmp_path):
    for payload in ('{"value": NaN}', '{"value": 1e999}'):
        path = tmp_path / "invalid.json"
        path.write_text(payload, encoding="utf-8")
        with pytest.raises(ValueError, match="non-finite"):
            _load_json(path)


def test_reference_contract_rejects_empty_companions_and_fake_generator(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "volume": 19,
                "generated_by": None,
                "generator_api": None,
                "data_policy": "synthetic-offline",
                "artifact_role": "fake",
                "metrics": {"fake": 1.0},
                "acceptance": {},
                "companions": {},
                "companion_schemas": {},
                "limitations": ["fake"],
                "semantic_sources": ["source.py"],
                "semantic_tests": ["test_source.py"],
            }
        ),
        encoding="utf-8",
    )
    findings = []
    _check_reference(
        path,
        19,
        findings,
        expected_semantic_sources=["source.py"],
        expected_semantic_tests=["test_source.py"],
        expected_companions=["reference/surfaces.npz"],
    )
    details = "\n".join(finding.detail for finding in findings)
    assert "generated_by" in details
    assert "generator_api" in details
    assert "companions must exactly match" in details
    assert "companion_schemas must exactly match" in details


def test_notebook_contract_rejects_unexecuted_code(tmp_path):
    path = tmp_path / "notebook.ipynb"
    path.write_text(
        json.dumps(
            {
                "metadata": {"johnhull": {"artifact_only": True}},
                "cells": [
                    {"cell_type": "markdown", "source": "## 限界\n## 参考文献"},
                    {
                        "cell_type": "code",
                        "source": "raise RuntimeError()",
                        "execution_count": None,
                        "outputs": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    findings = []
    _check_notebook(path, [], findings)
    assert any("unexecuted code cell" in finding.detail for finding in findings)


def test_committed_frontier_acceptance_is_canonical_and_passes():
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((root / "johnhull/release_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["volumes"]:
        reference = root / "johnhull/volumes" / item["slug"] / "reference"
        json_path = reference / next(
            Path(name).name for name in item["references"] if name.endswith(".json")
        )
        npz_path = reference / next(
            Path(name).name for name in item["references"] if name.endswith(".npz")
        )
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        with np.load(npz_path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        canonical = evaluate_acceptance(item["number"], payload["metrics"], arrays)
        assert payload["acceptance"] == canonical
        assert canonical["passed"] is True
        assert canonical["model_performance_approved"] is False


def test_reference_units_are_semantic_not_substring_guesses():
    root = Path(__file__).resolve().parents[3] / "johnhull/volumes"
    vol19 = json.loads(
        (root / "19_inverse_surfaces/reference/metrics.json").read_text(encoding="utf-8")
    )["companion_schemas"]["surfaces.npz"]
    vol25 = json.loads(
        (root / "25_climate_energy/reference/metrics.json").read_text(encoding="utf-8")
    )["companion_schemas"]["scenarios.npz"]
    assert vol19["teacher_maturities"]["unit"] == "years"
    assert vol19["teacher_standard_error"]["unit"] == "spot_units"
    assert vol25["premium_sensitivity"]["unit"] == "synthetic monetary units"
    assert vol25["ppa_volume_risk"]["unit"] == "synthetic monetary units"
    assert vol25["basis_rmse"]["unit"] == "weather payoff units"
