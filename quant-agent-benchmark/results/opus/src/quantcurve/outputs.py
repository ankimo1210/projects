"""Writing the machine-readable output contract.

Every file is written deterministically: rows are ordered, floats are formatted
with a fixed 12-significant-digit representation and JSON keys are sorted, so
two runs on the same input produce byte-identical files.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .workflow import WorkflowResult

__all__ = [
    "CURVE_COLUMNS",
    "CLEANING_COLUMNS",
    "REPRICING_COLUMNS",
    "RISK_COLUMNS",
    "write_outputs",
]

FLOAT_FORMAT = "%.12g"

CURVE_COLUMNS = ("maturity_years", "zero_rate", "discount_factor", "forward_rate")
CLEANING_COLUMNS = (
    "obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason",
)
REPRICING_COLUMNS = (
    "instrument_id", "instrument_type", "market_quote", "model_quote", "residual",
    "weight",
)
RISK_COLUMNS = ("instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y")


def _ordered(frame: pd.DataFrame, required: tuple[str, ...]) -> pd.DataFrame:
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"output frame is missing columns: {', '.join(missing)}")
    extras = [name for name in frame.columns if name not in required]
    return frame.loc[:, list(required) + sorted(extras)]


def _write_csv(frame: pd.DataFrame, path: Path, required: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ordered(frame, required).to_csv(
        path, index=False, float_format=FLOAT_FORMAT, lineterminator="\n"
    )


def _write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"object of type {type(value)!r} is not JSON serialisable")


def write_outputs(result: WorkflowResult, output_dir: str | Path) -> dict[str, Path]:
    """Write the full output contract and return the paths written."""
    root = Path(output_dir)
    paths = {
        "curve": root / "curves" / "curve.csv",
        "cleaning": root / "diagnostics" / "cleaning.csv",
        "repricing": root / "diagnostics" / "repricing.csv",
        "risk": root / "diagnostics" / "risk.csv",
        "model_comparison": root / "diagnostics" / "model_comparison.json",
        "sensitivity": root / "diagnostics" / "sensitivity.json",
        "validation": root / "diagnostics" / "validation_summary.json",
    }

    curve = result.curve_table.copy()
    if len(curve) < 361:
        raise ValueError("curve.csv must contain at least 361 grid rows")
    if curve["maturity_years"].iloc[0] > 1.0 / 12.0 + 1e-12:
        raise ValueError("curve.csv must start at or below 1/12 year")
    if curve["maturity_years"].iloc[-1] < 30.0 - 1e-12:
        raise ValueError("curve.csv must extend to at least 30 years")
    if not curve["maturity_years"].is_monotonic_increasing:
        raise ValueError("curve.csv rows must be ordered by maturity")
    if float(curve["discount_factor"].min()) <= 0.0:
        raise ValueError("curve.csv contains a non-positive discount factor")
    _write_csv(curve, paths["curve"], CURVE_COLUMNS)

    audit = result.cleaning.audit.copy()
    audit = audit.sort_values("obs_id", kind="stable").reset_index(drop=True)
    _write_csv(audit, paths["cleaning"], CLEANING_COLUMNS)
    _write_csv(result.repricing, paths["repricing"], REPRICING_COLUMNS)
    _write_csv(result.risk, paths["risk"], RISK_COLUMNS)

    _write_json(result.model_comparison, paths["model_comparison"])
    _write_json(result.sensitivity, paths["sensitivity"])
    _write_json(
        {
            "valuation_date": result.valuation_date.date().isoformat(),
            "market_data": str(result.market_data_path),
            "market_snapshot": result.market_snapshot,
            "observations": int(len(audit)),
            "usable_instruments": int(len(result.instruments)),
            "validation_flag_counts": result.validation_summary,
            "validation_findings": result.validation_findings,
            "cleaning_action_counts": result.cleaning.summary,
            "estimated_model_error_bp": result.model_error_bp,
            "warnings": result.warnings,
        },
        paths["validation"],
    )
    return paths
