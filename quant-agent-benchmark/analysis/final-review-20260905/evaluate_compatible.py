"""Run the original scorer with one documented schema-compatibility adapter.

The original risk join crashes on optional instrument_type/maturity_years
columns. Only the required reported risk fields are passed to that join;
instrument definitions and true_quote still come exclusively from evaluator
truth. No weights, formulas, thresholds, or other checks are changed.
"""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
import scoring

ORIGINAL_RISK_AGREEMENT = scoring.risk_agreement


def compatible_risk_agreement(curve, risk, truth_instruments):
    return ORIGINAL_RISK_AGREEMENT(curve, risk.loc[:, list(scoring.RISK_COLUMNS)], truth_instruments)


if __name__ == "__main__":
    scoring.risk_agreement = compatible_risk_agreement
    runpy.run_path(str(ROOT / "tools/evaluate_candidate.py"), run_name="__main__")
