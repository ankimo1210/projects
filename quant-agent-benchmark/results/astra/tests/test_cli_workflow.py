import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def run_cli(path, source=None, date="2026-01-15"):
    return subprocess.run([sys.executable, "-m", "quantcurve.cli", "run", "--market-data",
                           str(source or (ROOT / "data" / "market_observations.csv")),
                           "--output-dir", str(path), "--valuation-date", date],
                          cwd=ROOT, text=True, capture_output=True, env=os.environ.copy())


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}


def test_cli_end_to_end_reproducibility_and_contract(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    a, b = run_cli(first), run_cli(second)
    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout
    assert hashes(first) == hashes(second)
    curve = pd.read_csv(first / "curves" / "curve.csv")
    assert len(curve) >= 361
    assert curve.maturity_years.iloc[0] <= 1/12
    assert curve.maturity_years.iloc[-1] >= 30
    assert (curve.discount_factor > 0).all()
    assert np.isfinite(curve.to_numpy()).all()
    audit = pd.read_csv(first / "diagnostics" / "cleaning.csv")
    assert len(audit) == len(pd.read_csv(ROOT / "data" / "market_observations.csv"))
    reprice = pd.read_csv(first / "diagnostics" / "repricing.csv")
    risk = pd.read_csv(first / "diagnostics" / "risk.csv")
    assert set(reprice.instrument_id) == set(risk.instrument_id)
    assert {"key_2y", "key_5y", "key_10y", "key_30y", "dv01"} <= set(risk.columns)
    assert len(list((first / "charts").glob("*.png"))) == 5
    assert json.loads((first / "diagnostics" / "validation.json").read_text())["all_passed"]
    report = (first / "reports" / "research_report.html").read_text()
    assert report.count("data:image/png;base64,") == 5
    assert '<html lang="ja">' in report
    assert "http://" not in report and "https://" not in report


def test_cli_missing_input_nonzero_and_actionable(tmp_path):
    result = run_cli(tmp_path / "output", tmp_path / "missing.csv")
    assert result.returncode != 0
    assert "market data not found" in result.stderr
    assert not (tmp_path / "output").exists()


def test_cli_invalid_date_nonzero(tmp_path):
    result = run_cli(tmp_path / "output", date="not-a-date")
    assert result.returncode != 0
    assert "quantcurve:" in result.stderr


def test_cli_generalizes_to_supplied_subset_and_new_valuation_date(tmp_path):
    # A test-only subset of the supplied tape, not replacement research data.
    raw = pd.read_csv(ROOT / "data" / "market_observations.csv")
    subset = raw[~raw.obs_id.str.startswith("DUP")]
    source = tmp_path / "subset.csv"
    subset.to_csv(source, index=False)
    output = tmp_path / "result"
    result = run_cli(output, source, "2026-01-16")
    assert result.returncode == 0, result.stderr
    audit = pd.read_csv(output / "diagnostics" / "cleaning.csv")
    assert len(audit) == len(subset)
    report = (output / "reports" / "research_report.html").read_text()
    assert "評価日 2026-01-16" in report
    metadata = json.loads((output / "diagnostics" / "run_metadata.json").read_text())
    assert metadata["valuation_date"] == "2026-01-16"
