"""End-to-end research workflow: clean -> fit -> validate -> risk -> sensitivity -> write."""

from __future__ import annotations

import json
import math
import time
import warnings
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .advanced import AdvancedConfig, AdvancedFit, fit_advanced
from .baseline import fit_baseline
from .charts import chart_curves, chart_data_quality, chart_forwards, chart_model_comparison, chart_repricing, chart_risk, chart_sensitivity
from .cleaning import CleaningConfig, CleaningResult, clean_market_data
from .conventions import DEFAULT_STUB_RULE, StubRule
from .curve import PiecewiseLinearZeroCurve, ZeroCurve
from .instruments import Instrument, build_instrument
from .io import load_market_data
from .pricing import model_quote, rate_residual
from .risk import compute_risk, risk_verification_summary
from .sensitivity import run_sensitivity
from .validation import HoldoutResult, run_grouped_holdout, summarize_errors
from .weights import base_scales


@dataclass
class WorkflowOptions:
    market_data: Path
    output_dir: Path
    valuation_date: date
    report_dir: Path | None = None
    stub_rule: StubRule = DEFAULT_STUB_RULE
    lambda_fixed: float | None = None
    grid_step: float = 1.0 / 24.0
    grid_end: float = 30.0
    n_folds: int = 5
    max_stale_days: int = 0
    skip_sensitivity: bool = False
    noise_replications: int = 20
    seed: int = 20260115


@dataclass
class WorkflowResult:
    options: WorkflowOptions
    cleaning: CleaningResult
    table: pd.DataFrame
    instruments: list[Instrument]
    base_scale: np.ndarray
    baseline_curve: PiecewiseLinearZeroCurve
    adv: AdvancedFit
    final_weights_norm: np.ndarray
    repricing_advanced: pd.DataFrame
    repricing_baseline: pd.DataFrame
    train_metrics: dict
    holdout: HoldoutResult
    model_comparison: dict
    selected_model: str
    grid_baseline: pd.DataFrame
    grid_advanced: pd.DataFrame
    grid_selected: pd.DataFrame
    risk: pd.DataFrame
    risk_summary: dict
    sensitivity: dict
    sensitivity_deltas: pd.DataFrame | None
    warnings: list[str] = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    t_max: float = 30.0


def _repricing_table(instruments: list[Instrument], table: pd.DataFrame, curve: ZeroCurve, weights_norm: np.ndarray, factor: np.ndarray, std_res: np.ndarray | None, base_scale: np.ndarray) -> pd.DataFrame:
    rows = []
    for j, inst in enumerate(instruments):
        unit = 1.0 if inst.instrument_type == "bond" else 100.0
        mq = model_quote(inst, curve) * unit
        rows.append(
            {
                "instrument_id": inst.instrument_id,
                "instrument_type": inst.instrument_type,
                "obs_id": table["obs_id"].iloc[j],
                "maturity_years": inst.maturity,
                "market_quote": inst.quote * unit,
                "model_quote": mq,
                "residual": inst.quote * unit - mq,
                "residual_bp": rate_residual(inst, curve) * 1e4,
                "weight": float(weights_norm[j]),
                "robust_factor": float(factor[j]),
                "std_residual": float(std_res[j]) if std_res is not None else np.nan,
                "precision": float(1.0 / base_scale[j] ** 2),
            }
        )
    return pd.DataFrame(rows)


def _json_ready(obj):
    if isinstance(obj, dict):
        return {str(k): _json_ready(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_ready(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_json_ready(v) for v in obj.tolist()]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.DataFrame):
        return _json_ready(obj.to_dict(orient="records"))
    if isinstance(obj, (Path, date)):
        return str(obj)
    return obj


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=False) + "\n")


def run_workflow(opts: WorkflowOptions) -> WorkflowResult:
    t_start = time.perf_counter()
    timings: dict[str, float] = {}
    caught: list[str] = []
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        result = _run(opts, timings)
        for w in wlist:
            msg = f"{w.category.__name__}: {w.message} ({Path(str(w.filename)).name}:{w.lineno})"
            if msg not in caught:
                caught.append(msg)
    result.warnings = caught
    timings["total"] = time.perf_counter() - t_start
    result.timings = timings
    _write_outputs(result)
    return result


def _run(opts: WorkflowOptions, timings: dict) -> WorkflowResult:
    t0 = time.perf_counter()
    raw = load_market_data(opts.market_data)
    cleaning = clean_market_data(raw, opts.valuation_date, CleaningConfig(max_stale_days=opts.max_stale_days))
    table = cleaning.instruments
    if len(table) == 0:
        raise ValueError("no usable observations after validation; inspect the reasons in the cleaning audit (every row was excluded) and check --valuation-date against the quote timestamps")
    if not table["instrument_type"].isin(["deposit", "ois_swap"]).any():
        raise ValueError("no usable deposit or OIS quotes: a zero curve cannot be anchored from bonds alone with this workflow")
    instruments = [
        build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate, stub_rule=opts.stub_rule)
        for r in table.itertuples()
    ]
    types = table["instrument_type"].to_numpy()
    cluster_ids = table["tenor_cluster"].to_numpy()
    timings["cleaning"] = time.perf_counter() - t0

    # --- weights and baseline -----------------------------------------
    t0 = time.perf_counter()
    flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([float(np.median([i.quote for i in instruments if i.is_rate]))]))
    prelim_scale = base_scales(table, instruments, flat)
    prelim_base = fit_baseline(instruments, 1.0 / prelim_scale**2, cluster_ids)
    base_scale = base_scales(table, instruments, prelim_base)
    max_mat = float(max(i.maturity for i in instruments))
    t_max = float(max(opts.grid_end, math.ceil(max_mat)))
    cfg = AdvancedConfig(n_folds=opts.n_folds, lambda_fixed=opts.lambda_fixed)
    adv = fit_advanced(instruments, base_scale, types, cluster_ids, t_max, cfg)
    factor = adv.fit.robust_factor
    weights = adv.fit.weights
    weights_norm = weights / weights.max() if weights.max() > 0 else weights
    baseline_curve = fit_baseline(instruments, weights, cluster_ids)
    timings["fitting"] = time.perf_counter() - t0

    # --- repricing / in-sample metrics ---------------------------------
    rep_adv = _repricing_table(instruments, table, adv.curve, weights_norm, factor, adv.fit.std_residuals, base_scale)
    rep_base = _repricing_table(instruments, table, baseline_curve, weights_norm, factor, None, base_scale)
    kept = rep_adv["robust_factor"] > 0
    train_metrics = {
        "advanced": {"usable": summarize_errors(rep_adv[kept], "residual_bp"), "all": summarize_errors(rep_adv, "residual_bp")},
        "baseline": {"usable": summarize_errors(rep_base[kept], "residual_bp"), "all": summarize_errors(rep_base, "residual_bp")},
    }

    # --- holdout -------------------------------------------------------
    t0 = time.perf_counter()
    holdout = run_grouped_holdout(instruments, table, base_scale, factor, weights, cluster_ids, adv.folds, cfg, adv.lam, adv.power, adv.knots, t_max)
    timings["holdout"] = time.perf_counter() - t0
    ob, oa = holdout.metrics["baseline"]["overall"], holdout.metrics["advanced"]["overall"]
    hb, ha = ob["weighted_rmse_bp"], oa["weighted_rmse_bp"]
    ub, ua = ob["rmse_bp"], oa["rmse_bp"]
    if ha is not None and hb is not None and ha < hb:
        selected = "advanced"
        rel = (hb - ha) / hb * 100
        rationale = (
            f"The advanced penalised-spline model has the lower precision-weighted maturity-grouped holdout RMSE "
            f"({ha:.2f}bp vs {hb:.2f}bp for the bootstrap baseline, {rel:.0f}% lower; unweighted RMSE {ua:.2f}bp vs {ub:.2f}bp, "
            f"median absolute error {oa['median_abs_bp']:.2f}bp vs {ob['median_abs_bp']:.2f}bp, n={oa['n']} held-out instruments). "
        )
        if rel < 10:
            rationale += "The margin is small, so the simpler baseline remains a credible alternative; the advanced curve is preferred mainly for its smooth forward rates and its use of bond information. "
        if ua is not None and ub is not None and ua >= ub:
            rationale += "Note that the unweighted RMSE does not favour the advanced model; the difference is driven by a few illiquid quotes with very wide spreads. "
    else:
        selected = "baseline"
        rationale = (
            f"The bootstrap baseline has precision-weighted holdout RMSE {hb:.2f}bp versus {ha:.2f}bp for the advanced model (unweighted {ub:.2f}bp vs {ua:.2f}bp), "
            "so the extra complexity is not supported by out-of-sample evidence and the baseline is selected. "
        )
    by_type_notes = []
    for t in sorted(holdout.metrics["advanced"]["by_type"]):
        a = holdout.metrics["advanced"]["by_type"][t]["weighted_rmse_bp"]
        b = holdout.metrics["baseline"]["by_type"].get(t, {}).get("weighted_rmse_bp")
        if a is not None and b is not None:
            by_type_notes.append(f"{t}: advanced {a:.2f}bp vs baseline {b:.2f}bp (weighted)")
    rationale += "By type - " + "; ".join(by_type_notes) + "."
    model_comparison = {
        "selected_model": selected,
        "selection_rationale": rationale,
        "holdout_method": (
            f"Maturity-grouped {opts.n_folds}-fold cross-validation: instruments are grouped into tenor clusters "
            "(all quotes of the same tenor, and bonds maturing within 2% of each other, form one cluster); whole clusters "
            "are assigned round-robin in maturity order to folds so near-duplicate quotes never straddle train and test; "
            "the shortest and longest clusters always stay in the training set (extrapolation is not scored). Both models are "
            "refitted on every training fold. Errors are market-minus-model in yield-equivalent basis points (bond price errors "
            "divided by dollar duration). Instruments rejected by the full-data robust fit are not scored."
        ),
        "units": {"train": "yield-equivalent basis points (market minus model; bond price errors divided by dollar duration)", "holdout": "yield-equivalent basis points on held-out tenor clusters; weighted_rmse_bp uses precision 1/base_scale^2", "selection_metric": "holdout weighted_rmse_bp"},
        "baseline": {"description": "Sequential bootstrap over tenor-cluster quotes of deposits and OIS with linear interpolation of continuously compounded zero rates and flat zero extrapolation; bonds unused.", "units": "basis points (yield-equivalent)", "train": train_metrics["baseline"], "holdout": holdout.metrics["baseline"]},
        "advanced": {
            "description": "Cubic B-spline instantaneous forward curve with a maturity-weighted second-derivative roughness penalty (exponent fixed a priori), spread/liquidity/type-scale weights, leave-tenor-out and Tukey-biweight robust residual treatment, lambda chosen by grouped cross-validation.",
            "lambda": adv.lam,
            "lambda_cv_minimum": adv.cv.lam_min if adv.cv is not None else None,
            "penalty_power": adv.power,
            "knots": adv.knots.tolist(),
            "type_scales": adv.fit.type_scale,
            "irls_iterations": adv.fit.iterations,
            "irls_converged": adv.fit.converged,
            "n_rejected_by_robust_fit": int((factor == 0).sum()),
            "cv_table": adv.cv.table.drop(columns=["fold_scores"]).to_dict(orient="records") if adv.cv is not None else None,
            "cv_penalty_power_table": adv.cv.power_table.to_dict(orient="records") if adv.cv is not None and adv.cv.power_table is not None else None,
            "units": "basis points (yield-equivalent)",
            "train": train_metrics["advanced"],
            "holdout": holdout.metrics["advanced"],
        },
        "per_fold": holdout.per_fold.to_dict(orient="records"),
        "temporal_holdout": holdout.temporal,
    }

    # --- grids ----------------------------------------------------------
    n_steps = int(round(t_max / opts.grid_step))
    grid = np.arange(1, n_steps + 1) * opts.grid_step
    grid = grid[grid >= 1.0 / 12.0 - 1e-9]
    if grid[-1] < t_max - 1e-9:
        grid = np.append(grid, t_max)
    grid_base = baseline_curve.grid_frame(grid)
    grid_adv = adv.curve.grid_frame(grid)
    grid_sel = grid_adv if selected == "advanced" else grid_base
    selected_curve = adv.curve if selected == "advanced" else baseline_curve

    # --- risk -----------------------------------------------------------
    t0 = time.perf_counter()
    risk = compute_risk(instruments, selected_curve)
    risk.insert(3, "usable", factor > 0)
    risk_summary = risk_verification_summary(risk[risk["usable"]])
    timings["risk"] = time.perf_counter() - t0

    # --- sensitivity ---------------------------------------------------
    t0 = time.perf_counter()
    sens_grid = grid[:: max(1, int(round(0.25 / opts.grid_step)))]
    if opts.skip_sensitivity:
        sensitivity, deltas = {"skipped": {"condition": "sensitivity checks disabled with --skip-sensitivity", "results": {"n_checks": 0}, "interpretation": "no perturbation checks were run for this output"}}, None
    else:
        sensitivity, deltas = run_sensitivity(adv, instruments, table, base_scale, cluster_ids, cfg, t_max, opts.stub_rule, sens_grid, seed=opts.seed, n_noise=opts.noise_replications)
    timings["sensitivity"] = time.perf_counter() - t0

    # --- merge robust decisions into the audit trail ---------------------
    audit = cleaning.audit
    obs_to_idx = {o: j for j, o in enumerate(table["obs_id"])}
    for i in audit.index:
        j = obs_to_idx.get(audit.at[i, "obs_id"])
        if j is None:
            continue
        u = float(adv.fit.std_residuals[j])
        loo_flag = bool(adv.fit.loo.excluded[j]) if adv.fit.loo is not None else False
        audit.at[i, "weight"] = float(weights_norm[j])
        prefix = "" if audit.at[i, "reason"] == "passed all checks" else f"{audit.at[i, 'reason']}; "
        if factor[j] <= 0:
            audit.at[i, "action"] = "exclude"
            how = "leave-tenor-out screen" if loo_flag else "Tukey biweight"
            audit.at[i, "reason"] = f"{prefix}robust fit rejected ({how}, standardised residual u={u:.1f}, market-model={rep_adv['residual_bp'].iloc[j]:.1f}bp)"
        elif factor[j] < 0.5:
            if audit.at[i, "action"] in ("keep", "correct"):
                audit.at[i, "action"] = "downweight"
            audit.at[i, "reason"] = f"{prefix}robust down-weight (factor={factor[j]:.2f}, u={u:.1f})"
    cleaning.summary["actions"] = {k: int((audit["action"] == k).sum()) for k in ("keep", "correct", "downweight", "exclude")}
    cleaning.summary["n_rejected_by_robust_fit"] = int((factor == 0).sum())

    return WorkflowResult(
        options=opts,
        cleaning=cleaning,
        table=table,
        instruments=instruments,
        base_scale=base_scale,
        baseline_curve=baseline_curve,
        adv=adv,
        final_weights_norm=weights_norm,
        repricing_advanced=rep_adv,
        repricing_baseline=rep_base,
        train_metrics=train_metrics,
        holdout=holdout,
        model_comparison=model_comparison,
        selected_model=selected,
        grid_baseline=grid_base,
        grid_advanced=grid_adv,
        grid_selected=grid_sel,
        risk=risk,
        risk_summary=risk_summary,
        sensitivity=sensitivity,
        sensitivity_deltas=deltas,
        t_max=t_max,
    )


def _write_outputs(res: WorkflowResult) -> None:
    from .report import render_report

    out = Path(res.options.output_dir)
    curves, diag, charts = out / "curves", out / "diagnostics", out / "charts"
    for d in (curves, diag, charts):
        d.mkdir(parents=True, exist_ok=True)
    files = {}
    cols = ["maturity_years", "zero_rate", "discount_factor", "forward_rate"]
    res.grid_selected[cols].to_csv(curves / "curve.csv", index=False, float_format="%.12g")
    res.grid_baseline[cols].to_csv(curves / "curve_baseline.csv", index=False, float_format="%.12g")
    res.grid_advanced[cols].to_csv(curves / "curve_advanced.csv", index=False, float_format="%.12g")
    files["curve"] = curves / "curve.csv"
    audit_cols = ["obs_id", "instrument_id", "action", "normalized_quote", "weight", "reason", "instrument_type", "maturity_years", "raw_quote", "bid", "ask", "spread", "liquidity_score", "tenor_cluster", "source", "timestamp"]
    res.cleaning.audit[audit_cols].to_csv(diag / "cleaning.csv", index=False, float_format="%.10g")
    rep_cols = ["instrument_id", "instrument_type", "market_quote", "model_quote", "residual", "weight", "maturity_years", "residual_bp", "std_residual", "robust_factor", "obs_id"]
    selected_rep = res.repricing_advanced if res.selected_model == "advanced" else res.repricing_baseline
    selected_rep[rep_cols].to_csv(diag / "repricing.csv", index=False, float_format="%.10g")
    res.repricing_baseline[rep_cols].to_csv(diag / "repricing_baseline.csv", index=False, float_format="%.10g")
    res.repricing_advanced[rep_cols].to_csv(diag / "repricing_advanced.csv", index=False, float_format="%.10g")
    risk_cols = ["instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y", "instrument_type", "maturity_years", "usable", "pv", "key_sum", "analytic_dv01", "fd_vs_analytic_rel_diff", "key_sum_vs_dv01_rel_diff", "halfstep_vs_fullstep_rel_diff"]
    res.risk[risk_cols].to_csv(diag / "risk.csv", index=False, float_format="%.10g")
    write_json(diag / "model_comparison.json", res.model_comparison)
    write_json(diag / "sensitivity.json", res.sensitivity)
    write_json(diag / "risk_verification.json", res.risk_summary)
    res.holdout.predictions.to_csv(diag / "holdout_predictions.csv", index=False, float_format="%.10g")
    if res.adv.cv is not None:
        res.adv.cv.table.drop(columns=["fold_scores"]).to_csv(diag / "cv_table.csv", index=False, float_format="%.10g")
    if res.sensitivity_deltas is not None:
        res.sensitivity_deltas.to_csv(diag / "sensitivity_curve_deltas.csv", index=False, float_format="%.8g")
    # charts
    files["chart_curve"] = chart_curves(res.grid_baseline, res.grid_advanced, res.adv.knots, res.repricing_advanced, charts / "curve.png")
    files["chart_forward"] = chart_forwards(res.grid_baseline, res.grid_advanced, charts / "forward.png")
    files["chart_repricing"] = chart_repricing(res.repricing_advanced, res.cleaning.audit, charts / "repricing.png")
    files["chart_model_comparison"] = chart_model_comparison(res.adv.cv.table if res.adv.cv is not None else None, res.adv.cv.power_table if res.adv.cv is not None else None, res.adv.lam, res.holdout.metrics, res.holdout.per_fold, charts / "model_comparison.png")
    files["chart_data_quality"] = chart_data_quality(res.cleaning.audit, charts / "data_quality.png")
    if res.sensitivity_deltas is not None:
        files["chart_sensitivity"] = chart_sensitivity(res.sensitivity_deltas, charts / "sensitivity.png")
    files["chart_risk"] = chart_risk(res.risk[res.risk["usable"]], charts / "risk.png")
    # run summary
    summary = {
        "package_version": __version__,
        "valuation_date": str(res.options.valuation_date),
        "market_data": str(res.options.market_data),
        "stub_rule": res.options.stub_rule,
        "selected_model": res.selected_model,
        "lambda": res.adv.lam,
        "penalty_power": res.adv.power,
        "knots": res.adv.knots.tolist(),
        "t_max": res.t_max,
        "grid_rows": int(len(res.grid_selected)),
        "cleaning_summary": res.cleaning.summary,
        "type_scales": res.adv.fit.type_scale,
        "timings_seconds": res.timings,
        "numerical_warnings": res.warnings,
    }
    write_json(diag / "run_summary.json", summary)
    res.files = files
    report_dir = Path(res.options.report_dir) if res.options.report_dir else out / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    files["report"] = render_report(res, report_dir / "research_report.html")
