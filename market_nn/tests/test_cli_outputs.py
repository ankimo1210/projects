from __future__ import annotations

import json

import pandas as pd

from lob_reproductions import outputs
from lob_reproductions.cli import main
from lob_reproductions.outputs import write_run_artifacts
from lob_reproductions.provenance.profiles import load_profile


def test_cli_inspect_and_golden_commands(capsys) -> None:
    assert (
        main(
            [
                "inspect",
                "--profile",
                "deeplob_author_tf2_ff14d7c",
                "--show-shapes",
                "--show-parameters",
            ]
        )
        == 0
    )
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["parameter_count"]["total"] == 142_435
    assert inspected["shape_trace"][-1]["shape"] == [2, 3]

    assert main(["golden-test", "--profile", "tlob_author_repo_f1c0af4"]) == 0
    golden = json.loads(capsys.readouterr().out)
    assert golden["pass"] is True
    assert golden["checks"]["parameter_count"]["actual"] == 2_656_724


def test_output_contract_contains_identity_and_all_required_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(outputs, "project_root", lambda: tmp_path)
    profile = load_profile("deeplob_ieee_2019")
    destination = write_run_artifacts(
        profile=profile,
        metrics={"architecture_verified": True},
        predictions=pd.DataFrame({"sample_id": [0], "prediction": [1]}),
        shape_trace=[{"name": "output", "shape": [1, 3]}],
        parameter_count={"total": 60_947},
        warnings=[{"code": "SYNTHETIC_ONLY", "message": "synthetic test"}],
        actual_dataset_profile="deterministic_synthetic_smoke_v1",
    )
    assert {path.name for path in destination.iterdir()} == {
        "assumptions.json",
        "environment.json",
        "frozen_config.yaml",
        "git_state.json",
        "metrics.json",
        "parameter_count.json",
        "predictions.parquet",
        "report.md",
        "shape_trace.json",
        "source_manifest.json",
        "warnings.json",
    }
    identity = json.loads((destination / "source_manifest.json").read_text())
    assert identity["paper_id"] == "deeplob"
    assert identity["implementation_profile"] == "deeplob_ieee_2019"
    assert identity["fidelity_class"] == "B_PAPER_EXACT"
    assert identity["dataset_profile"] == "deterministic_synthetic_smoke_v1"
    assert identity["random_seed"] == 7
    assert (
        (destination / "report.md")
        .read_text()
        .startswith("# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA")
    )
