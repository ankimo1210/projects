from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import matplotlib.image as mpimg
import numpy as np
import pandas as pd


root = Path(sys.argv[1])
input_csv = Path(sys.argv[2])
required = [
    "pyproject.toml", "README.md", "MODEL_RISKS.md", "benchmark_summary.json",
    "outputs/curves/curve.csv", "outputs/diagnostics/cleaning.csv",
    "outputs/diagnostics/repricing.csv", "outputs/diagnostics/risk.csv",
    "outputs/diagnostics/model_comparison.json", "outputs/diagnostics/sensitivity.json",
    "reports/research_report.html", "outputs/charts/curve.png",
    "outputs/charts/forward_rate.png", "outputs/charts/repricing.png",
    "outputs/charts/model_comparison.png",
]
missing = [name for name in required if not (root / name).is_file() or (root / name).stat().st_size == 0]
assert not missing, missing

curve = pd.read_csv(root / "outputs/curves/curve.csv")
assert list(curve.columns) == ["maturity_years", "zero_rate", "discount_factor", "forward_rate"]
assert len(curve) >= 361 and curve.maturity_years.is_monotonic_increasing
assert curve.maturity_years.iloc[0] <= 1 / 12 + 1e-12 and curve.maturity_years.iloc[-1] >= 30
assert np.isfinite(curve.to_numpy()).all() and curve.discount_factor.gt(0).all()
assert np.max(np.abs(-np.log(curve.discount_factor) / curve.maturity_years - curve.zero_rate)) < 1e-10

cleaning = pd.read_csv(root / "outputs/diagnostics/cleaning.csv")
repricing = pd.read_csv(root / "outputs/diagnostics/repricing.csv")
risk = pd.read_csv(root / "outputs/diagnostics/risk.csv")
assert len(cleaning) == len(pd.read_csv(input_csv))
assert set(cleaning.action) <= {"keep", "correct", "downweight", "exclude"}
assert {"obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"} <= set(cleaning.columns)
assert {"instrument_id", "instrument_type", "market_quote", "model_quote", "residual", "weight"} <= set(repricing.columns)
assert {"instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y"} <= set(risk.columns)
assert len(repricing) == len(risk) and np.isfinite(repricing.select_dtypes("number").to_numpy()).all()
assert np.isfinite(risk.select_dtypes("number").to_numpy()).all()

comparison = json.loads((root / "outputs/diagnostics/model_comparison.json").read_text())
assert {"baseline", "advanced", "selected_model", "selection_rationale"} <= comparison.keys()
assert comparison["selected_model"] in {"baseline", "advanced"}
for model in ("baseline", "advanced"):
    for split in ("train", "holdout"):
        metrics = comparison[model][split]
        assert metrics["weighted_normalized_rmse_unit"] == "dimensionless_spread_units"
        assert {"by_tenor", "by_maturity_convention"} <= metrics["segments"].keys()

sensitivity = json.loads((root / "outputs/diagnostics/sensitivity.json").read_text())
assert len(sensitivity) >= 3
assert all({"condition", "numerical_results", "interpretation"} <= item.keys() for item in sensitivity.values())

report = (root / "reports/research_report.html").read_text()
for heading in (
    "Executive Summary", "Methodology", "Data Quality", "Model Comparison",
    "Sensitivity Analysis", "Validation and Repricing", "Charts", "Limitations",
    "Recommended Next Steps",
):
    assert heading in report
assert report.count("data:image/png;base64,") == 4
assert "/Users/" not in report and "file://" not in report

image_checks = {}
for name in ("curve.png", "forward_rate.png", "repricing.png", "model_comparison.png"):
    values = mpimg.imread(root / "outputs/charts" / name)
    assert values.shape[0] >= 400 and values.shape[1] >= 700
    assert np.isfinite(values).all() and float(np.std(values)) > 0.01
    image_checks[name] = {"shape": list(values.shape), "std": float(np.std(values))}

for relative in ["src", "tests", "configs", "examples"]:
    for path in (root / relative).rglob("*"):
        if path.is_file() and path.suffix in {".py", ".json", ".sh"}:
            text = path.read_text(errors="ignore")
            assert not re.search(r"/Users/|feedback_runs|baseline_workspace|audit/", text), path

summary = json.loads((root / "benchmark_summary.json").read_text())
for key in (
    "schema_version", "model_name", "reasoning_effort", "start_time", "finish_time",
    "wall_time_seconds", "test_runs", "failed_test_runs", "corrective_iterations",
    "tests_passed", "tests_failed", "files_created", "unresolved_limitations",
    "quota_percentage_consumed", "credits_consumed", "estimated_usd_cost", "human_interventions",
):
    assert key in summary, key

print(json.dumps({
    "status": "passed", "curve_rows": len(curve), "cleaning_rows": len(cleaning),
    "repricing_rows": len(repricing), "selected_model": comparison["selected_model"],
    "sensitivity_experiments": len(sensitivity), "embedded_charts": 4,
    "image_checks": image_checks,
}, indent=2))
