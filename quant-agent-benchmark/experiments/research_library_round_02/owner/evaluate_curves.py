"""Score retained curves without executing candidate code or editing old scores.

An external isolated runner must produce predictions/<case_id>/curve.csv.
Do not mount the private suite into that runner. Do not reveal per-case metrics
until all arms/repeats have frozen their submissions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import GRID, digest, save_json
from pricing import quote


def rmse(x):
    return float(np.sqrt(np.mean(np.square(x))))


def score_frame(prediction, truth, holdout):
    columns = ["maturity_years", "zero_rate", "discount_factor", "forward_rate"]
    values = prediction[columns].to_numpy(dtype=float)
    if len(values) < 361 or not np.isfinite(values).all():
        raise ValueError("curve needs >= 361 finite rows in all required columns")
    t, z, df, f = values.T
    if (np.diff(t) <= 0).any() or (t < 0).any() or t[0] > GRID[0] + 1e-9 or t[-1] < 30 - 1e-9:
        raise ValueError("curve grid must be unique, ordered, nonnegative and cover [1/12,30]")
    if (df <= 0).any() or not np.allclose(np.log(df), -t * z, atol=1e-7, rtol=0):
        raise ValueError("discount factors violate positivity or zero/discount consistency")
    zero = np.interp(GRID, t, z)
    forward = np.interp(GRID, t, f)
    true_z = np.interp(GRID, truth.maturity_years, truth.zero_rate)
    true_f = np.interp(GRID, truth.maturity_years, truth.forward_rate)
    # A common finite-difference diagnostic, not an exact analytic derivative.
    implied = np.gradient(GRID * zero, GRID, edge_order=2)
    error = (zero - true_z) * 1e4
    result = dict(
        zero_rmse_bp=rmse(error),
        forward_rmse_bp=rmse((forward - true_f) * 1e4),
        implied_forward_rmse_bp=rmse((implied - true_f) * 1e4),
        forward_consistency_rmse_bp=rmse((implied - forward) * 1e4),
    )
    for name, mask in (
        ("short", GRID <= 2),
        ("middle", (GRID > 2) & (GRID < 15)),
        ("long", GRID >= 15),
    ):
        result[f"zero_{name}_rmse_bp"] = rmse(error[mask])

    def discount(x):
        return np.exp(-np.asarray(x) * np.interp(x, np.r_[0, GRID], np.r_[zero[0], zero]))

    errors, scales = [], []
    for row in holdout.to_dict("records"):
        errors.append(quote(row, discount) - row["true_quote"])
        scales.append(0.01)  # 1 bp in PERCENT, or .01 price point; NOT both bp.
    result["holdout_normalized_rmse"] = rmse(np.asarray(errors) / scales)
    for kind, indices in holdout.reset_index(drop=True).groupby("instrument_type").groups.items():
        unit = "price_points" if kind == "bond" else "bp"
        factor = 1 if kind == "bond" else 100
        result[f"holdout_{kind}_rmse_{unit}"] = rmse(np.asarray(errors)[list(indices)] * factor)
    return result


def evaluate(suite, predictions):
    manifest = json.loads((suite / "manifest.json").read_text())
    for relative, expected in manifest["hashes"].items():
        if digest(suite / relative) != expected:
            raise ValueError(f"suite hash mismatch: {relative}")
    results = []
    for case in manifest["cases"]:
        if case["case_id"] == "training":
            continue
        name = case["case_id"]
        try:
            path = predictions / name / "curve.csv"
            metrics = score_frame(
                pd.read_csv(path),
                pd.read_csv(suite / name / "truth_curve.csv"),
                pd.read_csv(suite / name / "holdout.csv"),
            )
            results.append(
                dict(case_id=name, status="ok", prediction_sha256=digest(path), **metrics)
            )
        except (ValueError, KeyError, OSError) as exc:
            results.append(dict(case_id=name, status="failed", error=str(exc)))
    successful = [r for r in results if r["status"] == "ok"]
    complete = len(successful) == len(results)
    # No survivor-only headline: a failed/missing case blocks aggregate ranking.
    aggregate = (
        {
            key: float(np.mean([r[key] for r in successful]))
            for key in ("zero_rmse_bp", "forward_rmse_bp", "holdout_normalized_rmse")
        }
        if complete
        else None
    )
    return dict(
        contract_version="2.0",
        expected_cases=len(results),
        successful_cases=len(successful),
        failed_fraction=1 - len(successful) / len(results),
        comparable=complete,
        macro_mean=aggregate,
        cases=results,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite evaluation")
    result = evaluate(args.suite, args.predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}))
