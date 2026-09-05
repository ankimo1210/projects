"""Deterministic end-to-end workflow and machine-readable output contract."""
from __future__ import annotations

from datetime import date
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from .cleaning import clean_market_data
from .config import Config
from .io import load_market_data
from .pricing import risk_table
from .reporting import build_report, make_charts
from .research import compare_models, sensitivity_studies, sensitivity_contract


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def numerical_validation(frame, audit, curve, grid, risk, fits):
    t = grid.maturity_years.to_numpy()
    eps = 1e-5
    derivative = -(np.log(curve.discount(t + eps)) - np.log(curve.discount(t - eps))) / (2 * eps)
    forward_error = float(np.max(abs(derivative - grid.forward_rate.to_numpy())))
    checks = {
        "finite_curve": bool(np.isfinite(grid.to_numpy()).all()),
        "positive_discount_factors": bool((grid.discount_factor > 0).all()),
        "grid_coverage": bool(len(grid) >= 361 and t[0] <= 1 / 12 and t[-1] >= 30 and np.all(np.diff(t) > 0)),
        "zero_discount_consistency": bool(np.allclose(-np.log(grid.discount_factor) / t, grid.zero_rate, atol=1e-12, rtol=1e-12)),
        "forward_derivative_consistency": forward_error < 1e-8,
        "finite_risk": bool(np.isfinite(risk.select_dtypes(include="number").to_numpy()).all()),
        "dv01_step_consistency": bool(risk.fd_relative_error.max() < 1e-5),
        "key_aggregation_consistency": bool(risk.key_sum_relative_error.max() < 1e-5),
        "risk_covers_all_usable_instruments": set(risk.instrument_id) == set(frame.instrument_id),
        "excluded_weights_zero": bool((audit.loc[audit.action == "exclude", "weight"] == 0).all()),
        "all_optimizers_converged": all(x.converged for x in fits.values()),
    }
    result = {"all_passed": all(checks.values()), "checks": checks,
              "forward_max_absolute_fd_error": forward_error,
              "dv01_max_relative_half_step_error": float(risk.fd_relative_error.max()),
              "key_max_relative_aggregation_error": float(risk.key_sum_relative_error.max()),
              "grid_rows": len(grid), "min_discount_factor": float(grid.discount_factor.min()),
              "max_discount_factor": float(grid.discount_factor.max()),
              "zero_range": [float(grid.zero_rate.min()), float(grid.zero_rate.max())],
              "forward_range": [float(grid.forward_rate.min()), float(grid.forward_rate.max())],
              "scope": "Numerical invariants, not verification against an independent market truth."}
    if not result["all_passed"]:
        raise RuntimeError("numerical validation failed: " + ", ".join(k for k, v in checks.items() if not v))
    return result


def run_workflow(market_data, output_dir, valuation_date, config=Config()):
    # Parse data and date before creating outputs; invalid input is actionable.
    if date.fromisoformat(valuation_date).isoformat() != valuation_date:
        raise ValueError("valuation-date must have YYYY-MM-DD format")
    source = Path(market_data)
    raw = load_market_data(source)
    frame, audit = clean_market_data(raw, valuation_date, config)
    comparison, fits, holdout = compare_models(frame, config)
    sensitivity, sensitivity_curves = sensitivity_studies(frame, fits, comparison, config)
    selected_name = comparison["selected_model"]
    selected = fits[selected_name]
    for i, r in enumerate(frame.itertuples()):
        idx = r.row_id
        w = selected.robust_weights[i]
        audit.loc[idx, "weight"] = r.base_weight * w
        audit.loc[idx, "robust_weight"] = w
        audit.loc[idx, "advanced_robust_weight"] = fits["advanced"].robust_weights[i]
        if w < 0.999:
            audit.loc[idx, "action"] = "downweight"
            audit.loc[idx, "reason"] += f"; selected-model robust residual downweight={w:.8g} (Huber threshold {config.huber_threshold:g} sigma)"
    audit["robust_weight"] = audit.robust_weight.fillna(0)
    audit["advanced_robust_weight"] = audit.advanced_robust_weight.fillna(0)
    t = np.linspace(1 / 12, 30, config.grid_rows)

    def curve_frame(curve):
        return pd.DataFrame({"maturity_years": t, "zero_rate": curve.zero(t),
                             "discount_factor": curve.discount(t), "forward_rate": curve.forward(t)})

    grid = curve_frame(selected.curve)
    risk = risk_table(frame, selected.curve)
    validation = numerical_validation(frame, audit, selected.curve, grid, risk, fits)
    repricing = frame[["obs_id", "instrument_id", "instrument_type", "maturity_years"]].copy()
    repricing["market_quote"] = frame.normalized_quote
    repricing["model_quote"] = selected.quotes
    repricing["residual"] = selected.quotes - frame.normalized_quote.to_numpy()
    repricing["weight"] = frame.base_weight.to_numpy() * selected.robust_weights
    repricing["robust_weight"] = selected.robust_weights
    repricing["sigma"] = frame.sigma
    repricing["standardized_residual"] = repricing.residual / repricing.sigma
    repricing["bid"] = frame.normalized_bid
    repricing["ask"] = frame.normalized_ask
    repricing["visible_holdout_member"] = holdout
    repricing["fit_scope"] = "full_sample_refit"
    for kind, fit in fits.items():
        repricing[f"{kind}_model_quote"] = fit.quotes
    quality = {"input_rows": len(raw), "usable_instruments": len(frame),
               "final_action_counts": {str(k): int(v) for k, v in audit.action.value_counts().items()},
               "reason_counts": {s: int(audit.reason.str.contains(s, regex=False).sum()) for s in
                                 ("stale observation", "duplicate instrument_id", "missing quote recovered", "inverted bid/ask", "mislabelled rate units", "price-per-face unit mismatch", "illiquid", "robust residual downweight")},
               "effective_precision_definition": "weight = liquidity/reliability × robust_weight / sigma^2; units inverse normalized quote squared",
               "excluded_obs_ids": audit.loc[audit.action == "exclude", "obs_id"].tolist()}
    output = Path(output_dir)
    for sub in ("curves", "diagnostics", "charts", "reports"):
        (output / sub).mkdir(parents=True, exist_ok=True)
    for kind, fit in fits.items():
        curve_frame(fit.curve).to_csv(output / "curves" / f"{kind}_curve.csv", index=False, float_format="%.12g")
    grid.to_csv(output / "curves" / "curve.csv", index=False, float_format="%.12g")
    # Put the required audit fields first; preserve original fields and reasons.
    front = ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]
    audit = audit[front + [c for c in audit.columns if c not in front]]
    audit.to_csv(output / "diagnostics" / "cleaning.csv", index=False, float_format="%.12g")
    repricing.to_csv(output / "diagnostics" / "repricing.csv", index=False, float_format="%.12g")
    risk.to_csv(output / "diagnostics" / "risk.csv", index=False, float_format="%.12g")
    pd.DataFrame(comparison["holdout_predictions"]).to_csv(output / "diagnostics" / "holdout_repricing.csv", index=False, float_format="%.12g")
    for name, data in (("model_comparison.json", comparison), ("sensitivity.json", sensitivity_contract(sensitivity, config)),
                       ("validation.json", validation), ("data_quality.json", quality),
                       ("model_parameters.json", {k: fit.curve.to_dict() for k, fit in fits.items()}),
                       ("configuration.json", config.to_dict())):
        write_json(output / "diagnostics" / name, data)
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "matplotlib")}
    dataset_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    write_json(output / "diagnostics" / "run_metadata.json", {"python": platform.python_version(), "packages": versions,
               "valuation_date": valuation_date, "input_sha256": dataset_hash, "random_seed": config.seed,
               "selected_model": selected_name, "network_required_for_workflow": False})
    charts = make_charts(output, frame, fits, selected_name, comparison, sensitivity_curves)
    report = build_report(output, frame, audit, comparison, sensitivity, validation, charts, config, dataset_hash, valuation_date)
    (output / "reports" / "research_report.html").write_text(report, encoding="utf-8")
    return {"selected_model": selected_name, "usable_instruments": len(frame),
            "grid_rows": len(grid), "validation_passed": validation["all_passed"],
            "holdout_improvement": comparison["relative_holdout_improvement"]}
