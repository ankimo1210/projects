"""End-to-end deterministic zero-curve research workflow."""

from __future__ import annotations

from dataclasses import asdict, replace
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cleaning import apply_robust_audit, clean_market_data
from .config import CurveConfig
from .conventions import discount_array_from_zero
from .io import load_market_data
from .modeling import (
    fit_advanced,
    fit_baseline,
    fit_metrics,
    maturity_holdout_mask,
    quote_scales,
    repricing_residuals,
)
from .reporting import build_html_report, create_charts
from .risk import instrument_risk, risk_validation


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sensitivity_analysis(rows: pd.DataFrame, reference_curve, cfg: CurveConfig) -> dict[str, object]:
    grid = np.linspace(1.0 / 12.0, 30.0, 361)
    reference_zero = np.asarray(reference_curve.zero(grid))
    baseline = fit_baseline(rows, cfg).curve
    smoothing = {}
    for value in (0.2, 2.0, 20.0):
        local_cfg = replace(cfg, smoothing_lambda=value)
        fit = fit_advanced(rows, local_cfg, baseline)
        delta = 10_000 * (np.asarray(fit.curve.zero(grid)) - reference_zero)
        smoothing[str(value)] = {
            "success": fit.success,
            "max_abs_zero_delta_bp": float(np.max(np.abs(delta))),
            "weighted_normalized_rmse": fit_metrics(rows, fit.curve, local_cfg)["weighted_normalized_rmse"],
        }
    thresholds = {}
    for value in (2.0, 3.0, 4.0):
        local_cfg = replace(cfg, outlier_threshold=value)
        fit = fit_advanced(rows, local_cfg, baseline)
        delta = 10_000 * (np.asarray(fit.curve.zero(grid)) - reference_zero)
        thresholds[str(value)] = {
            "downweighted_count": int(np.sum(fit.robust_multipliers < 0.999)),
            "max_abs_zero_delta_bp": float(np.max(np.abs(delta))),
            "weighted_normalized_rmse": fit_metrics(rows, fit.curve, local_cfg)["weighted_normalized_rmse"],
        }
    rng = np.random.default_rng(cfg.seed)
    remove_count = max(1, int(np.floor(0.10 * len(rows))))
    removed_positions = np.sort(rng.choice(len(rows), size=remove_count, replace=False))
    reduced = rows.drop(rows.index[removed_positions]).reset_index(drop=True)
    removal_fit = fit_advanced(reduced, cfg, fit_baseline(reduced, cfg).curve)
    removal_delta = 10_000 * (np.asarray(removal_fit.curve.zero(grid)) - reference_zero)
    unweighted = rows.copy()
    unweighted["fit_weight"] = 1.0
    unweighted["base_weight"] = 1.0
    unweighted_fit = fit_advanced(unweighted, cfg, fit_baseline(unweighted, cfg).curve)
    liquidity_delta = 10_000 * (np.asarray(unweighted_fit.curve.zero(grid)) - reference_zero)
    short_grid = np.linspace(1.0 / 12.0, 1.0, 80)
    long_grid = np.linspace(20.0, 30.0, 120)
    return {
        "smoothing_parameter": smoothing,
        "outlier_threshold": thresholds,
        "remove_10_percent": {
            "seed": cfg.seed,
            "removed_count": int(remove_count),
            "max_abs_zero_delta_bp": float(np.max(np.abs(removal_delta))),
            "rmse_zero_delta_bp": float(np.sqrt(np.mean(removal_delta**2))),
        },
        "liquidity_weighting": {
            "max_abs_zero_delta_without_weights_bp": float(np.max(np.abs(liquidity_delta))),
            "rmse_zero_delta_without_weights_bp": float(np.sqrt(np.mean(liquidity_delta**2))),
        },
        "end_behaviour": {
            "short_end_zero_range_percent": [float(100 * np.min(reference_curve.zero(short_grid))), float(100 * np.max(reference_curve.zero(short_grid)))],
            "short_end_forward_range_percent": [float(100 * np.min(reference_curve.forward(short_grid))), float(100 * np.max(reference_curve.forward(short_grid)))],
            "long_end_zero_range_percent": [float(100 * np.min(reference_curve.zero(long_grid))), float(100 * np.max(reference_curve.zero(long_grid)))],
            "long_end_forward_range_percent": [float(100 * np.min(reference_curve.forward(long_grid))), float(100 * np.max(reference_curve.forward(long_grid)))],
        },
    }


def run_workflow(
    market_data: str | Path,
    output_dir: str | Path,
    valuation_date: str,
    report_path: str | Path | None = None,
    config: CurveConfig | None = None,
) -> dict[str, object]:
    cfg = config or CurveConfig()
    destination = Path(output_dir)
    curve_dir = destination / "curves"
    diagnostic_dir = destination / "diagnostics"
    chart_dir = destination / "charts"
    for directory in (curve_dir, diagnostic_dir, chart_dir):
        directory.mkdir(parents=True, exist_ok=True)

    raw = load_market_data(market_data)
    cleaned = clean_market_data(raw, valuation_date, cfg)
    rows = cleaned.usable.reset_index(drop=True)
    if len(rows) < 10 or rows["instrument_type"].nunique() < 2:
        raise ValueError("insufficient usable cross-instrument observations for curve estimation")

    holdout_mask = maturity_holdout_mask(rows, cfg)
    train = rows.loc[~holdout_mask].reset_index(drop=True)
    holdout = rows.loc[holdout_mask].reset_index(drop=True)
    if len(train) < 8 or len(holdout) < 3:
        raise ValueError("maturity-block holdout produced insufficient train or validation observations")

    baseline_train = fit_baseline(train, cfg)
    advanced_train = fit_advanced(train, cfg, baseline_train.curve)
    comparison: dict[str, object] = {
        "holdout_method": "deterministic 0.5Y maturity buckets where bucket_index mod 5 equals 3; whole buckets held together",
        "baseline": {
            "description": "spread/liquidity-weighted half-year median standalone yields with PCHIP",
            "train": fit_metrics(train, baseline_train.curve, cfg),
            "holdout": fit_metrics(holdout, baseline_train.curve, cfg),
        },
        "advanced": {
            "description": "natural-cubic zero knots, curvature penalty, spread/liquidity weights, IRLS Huber outliers",
            "train": fit_metrics(train, advanced_train.curve, cfg),
            "holdout": fit_metrics(holdout, advanced_train.curve, cfg),
            "optimizer_success": advanced_train.success,
        },
    }
    baseline_holdout = float(comparison["baseline"]["holdout"]["weighted_normalized_rmse"])
    advanced_holdout = float(comparison["advanced"]["holdout"]["weighted_normalized_rmse"])
    dense = np.linspace(0.0, 30.0, 1001)
    advanced_guardrails = (
        advanced_train.success
        and np.all(np.isfinite(advanced_train.curve.zero(dense)))
        and np.all(np.asarray(advanced_train.curve.discount(dense)) > 0)
        and np.max(np.abs(advanced_train.curve.forward(dense))) < 0.25
    )
    baseline_guardrails = (
        np.all(np.isfinite(baseline_train.curve.zero(dense)))
        and np.all(np.asarray(baseline_train.curve.discount(dense)) > 0)
        and np.max(np.abs(baseline_train.curve.forward(dense))) < 0.25
    )
    comparison["baseline"]["numerical_guardrails_passed"] = bool(baseline_guardrails)
    comparison["advanced"]["numerical_guardrails_passed"] = bool(advanced_guardrails)
    if advanced_guardrails and not baseline_guardrails:
        selected_name = "advanced"
        rationale = "Baseline failed the predeclared forward-rate stability guardrail; advanced model passed. Selection is based on numerical stability, not complexity."
    elif advanced_guardrails and advanced_holdout < 0.98 * baseline_holdout:
        selected_name = "advanced"
        rationale = "Advanced model cleared numerical guardrails and improved visible holdout normalized RMSE by more than 2%."
    else:
        selected_name = "baseline"
        rationale = "Advanced model did not clear both the numerical guardrails and the predeclared 2% holdout-improvement hurdle; baseline retained."
    comparison["selected_model"] = selected_name
    comparison["selection_rationale"] = rationale

    baseline_full = fit_baseline(rows, cfg)
    advanced_full = fit_advanced(rows, cfg, baseline_full.curve)
    if not advanced_full.success:
        raise RuntimeError(f"advanced full-data optimizer failed: {advanced_full.message}")
    cleaned = apply_robust_audit(cleaned, advanced_full.robust_multipliers, advanced_full.robust_scores)
    rows = cleaned.usable.reset_index(drop=True)
    selected_curve = advanced_full.curve if selected_name == "advanced" else baseline_full.curve

    grid = np.linspace(1.0 / 12.0, 30.0, 361)
    zero = np.asarray(selected_curve.zero(grid))
    discounts = discount_array_from_zero(zero, grid)
    forwards = np.asarray(selected_curve.forward(grid))
    curve_table = pd.DataFrame(
        {"maturity_years": grid, "zero_rate": zero, "discount_factor": discounts, "forward_rate": forwards}
    )
    curve_table.to_csv(curve_dir / "curve.csv", index=False, float_format="%.12g")

    cleaning_columns = ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason"]
    cleaned.audit.loc[:, cleaning_columns].to_csv(diagnostic_dir / "cleaning.csv", index=False, float_format="%.12g")
    residuals = repricing_residuals(rows, selected_curve)
    standardized = residuals / quote_scales(rows, cfg)
    repricing = pd.DataFrame(
        {
            "instrument_id": rows["instrument_id"].to_numpy(),
            "instrument_type": rows["instrument_type"].to_numpy(),
            "maturity_years": rows["maturity_years"].to_numpy(),
            "market_quote": rows["normalized_quote"].to_numpy(),
            "model_quote": rows["normalized_quote"].to_numpy() + residuals,
            "residual": residuals,
            "standardized_residual": standardized,
            "weight": rows["fit_weight"].to_numpy(),
        }
    )
    repricing.to_csv(diagnostic_dir / "repricing.csv", index=False, float_format="%.12g")
    risk = instrument_risk(rows, selected_curve)
    risk.to_csv(diagnostic_dir / "risk.csv", index=False, float_format="%.12g")

    sensitivity = _sensitivity_analysis(rows, advanced_full.curve, cfg)
    risk_checks = risk_validation(rows, selected_curve)
    transform_error = float(np.max(np.abs(-np.log(discounts) / grid - zero)))
    validation: dict[str, object] = {
        "curve_rows": int(len(curve_table)),
        "curve_start_years": float(grid[0]),
        "curve_end_years": float(grid[-1]),
        "all_outputs_finite": bool(np.isfinite(curve_table.to_numpy()).all() and np.isfinite(risk.select_dtypes("number").to_numpy()).all()),
        "all_discount_factors_positive": bool(np.all(discounts > 0)),
        "zero_discount_round_trip_max_abs_error": transform_error,
        "max_adjacent_zero_change_bp": float(10_000 * np.max(np.abs(np.diff(zero)))),
        "min_discount_factor": float(np.min(discounts)),
        "max_discount_factor": float(np.max(discounts)),
        "min_forward_rate": float(np.min(forwards)),
        "max_forward_rate": float(np.max(forwards)),
        "selected_full_sample_metrics": fit_metrics(rows, selected_curve, cfg),
        "risk_checks": risk_checks,
    }
    if not all(
        [validation["all_outputs_finite"], validation["all_discount_factors_positive"], transform_error < 1e-12, risk_checks["key_sum_consistent"], risk_checks["finite_difference_consistent"]]
    ):
        raise RuntimeError(f"numerical validation failed: {validation}")

    _write_json(diagnostic_dir / "model_comparison.json", comparison)
    _write_json(diagnostic_dir / "sensitivity.json", sensitivity)
    _write_json(diagnostic_dir / "validation.json", validation)
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "matplotlib")}
    metadata = {
        "valuation_date": valuation_date,
        "random_seed": cfg.seed,
        "config": asdict(cfg),
        "dependencies": versions,
        "input_rows": int(len(raw)),
        "usable_instruments": int(len(rows)),
        "holdout_rows": int(len(holdout)),
    }
    _write_json(diagnostic_dir / "run_metadata.json", metadata)

    charts = create_charts(chart_dir, selected_curve, baseline_full.curve, advanced_full.curve, repricing, comparison)
    final_report = Path(report_path) if report_path is not None else destination / "reports" / "research_report.html"
    config_summary = {
        "smoothing lambda": cfg.smoothing_lambda,
        "Huber threshold": cfg.outlier_threshold,
        "robust iterations": advanced_full.iterations,
        "zero-rate knots": len(advanced_full.curve.knots),
        "fixed seed": cfg.seed,
    }
    build_html_report(final_report, valuation_date, comparison, sensitivity, validation, cleaned.audit, repricing, charts, config_summary)
    return {
        "selected_model": selected_name,
        "usable_instruments": int(len(rows)),
        "excluded_observations": int((cleaned.audit["action"] == "exclude").sum()),
        "downweighted_observations": int((cleaned.audit["action"] == "downweight").sum()),
        "report_path": str(final_report),
        "validation": validation,
    }
