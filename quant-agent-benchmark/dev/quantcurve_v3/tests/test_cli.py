from __future__ import annotations

import filecmp
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quantcurve.cli import main
from synthetic import synthetic_frame

REQUIRED = {
    "curves/curve.csv": ["maturity_years", "zero_rate", "discount_factor", "forward_rate"],
    "diagnostics/cleaning.csv": ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"],
    "diagnostics/repricing.csv": ["instrument_id", "instrument_type", "market_quote", "model_quote", "residual", "weight"],
    "diagnostics/risk.csv": ["instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y"],
}


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    frame = synthetic_frame(noise_bp=0.3, seed=11)
    # a few defects so every cleaning path is exercised end to end
    frame.loc[3, "quote_value"] = np.nan
    frame.loc[8, ["quote_value", "bid", "ask"]] = frame.loc[8, ["quote_value", "bid", "ask"]] / 100.0
    frame.loc[20, "timestamp"] = "2026-01-02T15:00:00Z"
    path = tmp_path_factory.mktemp("data") / "obs.csv"
    frame.to_csv(path, index=False)
    return path


def _run(dataset: Path, out: Path, extra: list[str] | None = None) -> int:
    args = ["run", "--market-data", str(dataset), "--output-dir", str(out), "--valuation-date", "2026-01-15", "--quiet"]
    return main(args + (extra or []))


def test_end_to_end_outputs(dataset, tmp_path):
    out = tmp_path / "out"
    assert _run(dataset, out, ["--noise-replications", "3"]) == 0
    for rel, cols in REQUIRED.items():
        df = pd.read_csv(out / rel)
        assert list(df.columns[: len(cols)]) == cols, rel
        assert len(df) > 0
    curve = pd.read_csv(out / "curves/curve.csv")
    assert len(curve) >= 361
    assert curve["maturity_years"].iloc[0] <= 1 / 12 + 1e-9 and curve["maturity_years"].iloc[-1] >= 30 - 1e-9
    assert (np.diff(curve["maturity_years"]) > 0).all()
    assert np.isfinite(curve.to_numpy()).all() and (curve["discount_factor"] > 0).all()
    np.testing.assert_allclose(np.exp(-curve["zero_rate"] * curve["maturity_years"]), curve["discount_factor"], rtol=1e-9)
    cleaning = pd.read_csv(out / "diagnostics/cleaning.csv")
    assert len(cleaning) == len(pd.read_csv(dataset))
    assert set(cleaning["action"]).issubset({"keep", "correct", "downweight", "exclude"})
    assert cleaning["weight"].between(0, 1).all()
    assert (cleaning.loc[cleaning["action"] == "exclude", "weight"] == 0).all()
    mc = json.loads((out / "diagnostics/model_comparison.json").read_text())
    for key in ("selected_model", "selection_rationale", "baseline", "advanced", "holdout_method"):
        assert key in mc
    assert mc["baseline"]["holdout"]["overall"]["rmse_bp"] is not None
    assert mc["advanced"]["train"]["usable"]["overall"]["rmse_bp"] is not None
    sens = json.loads((out / "diagnostics/sensitivity.json").read_text())
    named = {k: v for k, v in sens.items() if k != "skipped"}
    assert len(named) >= 3
    assert all(isinstance(v, dict) and v["condition"] and v["results"] and v["interpretation"] for v in named.values())
    assert "stub_rule_forward_actual" in named
    mc = json.loads((out / "diagnostics/model_comparison.json").read_text())
    for key in ("baseline", "advanced", "selected_model", "selection_rationale"):
        assert key in mc
    for m in ("baseline", "advanced"):
        assert "units" in mc[m] and "by_tenor_band" in mc[m]["holdout"]
    charts = list((out / "charts").glob("*.png"))
    names = {p.stem for p in charts}
    assert {"curve", "forward", "repricing", "model_comparison"}.issubset(names)
    assert all(p.stat().st_size > 1000 for p in charts)
    report = out / "reports" / "research_report.html"
    text = report.read_text(encoding="utf-8")
    for section in ("Executive Summary", "Methodology", "Data Quality", "Model Comparison", "Sensitivity Analysis", "Validation and Repricing", "Charts", "Limitations", "Recommended Next Steps"):
        assert section in text
    assert "data:image/png;base64" in text
    risk = pd.read_csv(out / "diagnostics/risk.csv")
    assert np.isfinite(risk[["dv01", "key_2y", "key_5y", "key_10y", "key_30y"]].to_numpy()).all()


def test_deterministic(dataset, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert _run(dataset, a, ["--skip-sensitivity"]) == 0
    assert _run(dataset, b, ["--skip-sensitivity"]) == 0
    for rel in ("curves/curve.csv", "diagnostics/cleaning.csv", "diagnostics/repricing.csv", "diagnostics/risk.csv", "diagnostics/model_comparison.json"):
        assert filecmp.cmp(a / rel, b / rel, shallow=False), rel


def test_report_dir_option_and_stub_rule(dataset, tmp_path):
    out, rep = tmp_path / "out", tmp_path / "rep"
    assert _run(dataset, out, ["--skip-sensitivity", "--report-dir", str(rep), "--stub-rule", "round", "--lambda", "5"]) == 0
    assert (rep / "research_report.html").is_file()
    summary = json.loads((out / "diagnostics/run_summary.json").read_text())
    assert summary["stub_rule"] == "round" and summary["lambda"] == 5.0


def test_input_errors_exit_nonzero(dataset, tmp_path, capsys):
    assert main(["run", "--market-data", str(tmp_path / "missing.csv"), "--output-dir", str(tmp_path / "o"), "--valuation-date", "2026-01-15"]) == 2
    assert "not found" in capsys.readouterr().err
    assert main(["run", "--market-data", str(dataset), "--output-dir", str(tmp_path / "o"), "--valuation-date", "15/01/2026"]) == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"obs_id": ["x"]}).to_csv(bad, index=False)
    assert main(["run", "--market-data", str(bad), "--output-dir", str(tmp_path / "o"), "--valuation-date", "2026-01-15"]) == 2
    assert "missing required columns" in capsys.readouterr().err
    # every quote stale relative to the valuation date -> actionable error
    assert main(["run", "--market-data", str(dataset), "--output-dir", str(tmp_path / "o"), "--valuation-date", "2026-03-01"]) == 2
    assert "valuation-date" in capsys.readouterr().err


def test_report_head_is_well_formed(dataset, tmp_path):
    """feedback_round_01: the report must declare utf-8 and interpolate its title/CSS (a browser check caught a literal '{CSS}')."""
    out = tmp_path / "o"
    assert _run(dataset, out, ["--skip-sensitivity"]) == 0
    text = (out / "reports" / "research_report.html").read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>") and "<meta charset='utf-8'>" in text
    assert "{CSS}" not in text and "{html.escape" not in text and "<style>:root" in text.replace("\n", "")
    assert text.rstrip().endswith("</html>")
