from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd

from helpers import write_market_csv


def test_cli_and_end_to_end_reproducibility(tmp_path: Path) -> None:
    market = write_market_csv(tmp_path / "market.csv")
    project_root = Path(__file__).resolve().parents[1]
    source_root = project_root / "src"
    outputs = []
    for name in ("run_a", "run_b"):
        destination = tmp_path / name
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source_root)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "quantcurve.cli",
                "run",
                "--market-data",
                str(market),
                "--output-dir",
                str(destination),
                "--valuation-date",
                "2026-01-15",
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        outputs.append(destination)
    first, second = outputs
    assert (first / "curves" / "curve.csv").read_bytes() == (second / "curves" / "curve.csv").read_bytes()
    curve = pd.read_csv(first / "curves" / "curve.csv")
    assert len(curve) >= 361
    assert curve.discount_factor.gt(0).all()
    for relative in (
        "diagnostics/cleaning.csv",
        "diagnostics/repricing.csv",
        "diagnostics/risk.csv",
        "diagnostics/model_comparison.json",
        "diagnostics/sensitivity.json",
        "charts/curve.png",
        "charts/forward_rate.png",
        "charts/repricing.png",
        "charts/model_comparison.png",
        "reports/research_report.html",
    ):
        assert (first / relative).is_file() and (first / relative).stat().st_size > 0
    comparison = json.loads((first / "diagnostics" / "model_comparison.json").read_text())
    assert comparison["selected_model"] in {"baseline", "advanced"}
    assert {"baseline", "advanced", "selected_model", "selection_rationale"} <= comparison.keys()
    for model in ("baseline", "advanced"):
        for split in ("train", "holdout"):
            assert comparison[model][split]["weighted_normalized_rmse_unit"] == "dimensionless_spread_units"
            assert "segments" in comparison[model][split]
    sensitivity = json.loads((first / "diagnostics" / "sensitivity.json").read_text())
    assert len(sensitivity) >= 3
    assert all({"condition", "numerical_results", "interpretation"} <= experiment.keys() for experiment in sensitivity.values())
    report = (first / "reports" / "research_report.html").read_text()
    assert "Valuation date: 2026-01-15" in report
    for heading in (
        "Executive Summary", "Methodology", "Data Quality", "Model Comparison",
        "Sensitivity Analysis", "Validation and Repricing", "Charts", "Limitations",
        "Recommended Next Steps",
    ):
        assert heading in report
