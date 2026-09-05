"""End-to-end research workflow: load, validate, clean, fit, validate, report.

The pipeline is a straight line and every stage is separately testable:

1. **load** the CSV with a per-cell parse audit;
2. **validate** it against every documented schema, range, unit, timestamp,
   two-way-market and duplicate rule;
3. **clean** it into normalised instruments with an audited action and weight;
4. **calibrate the error model**: a preliminary robust fit gives the per-type
   dispersion of repricing residuals, which is added to the quote uncertainty in
   quadrature.  This is what stops bond idiosyncratic spreads -- far wider than
   any bond's bid/ask -- from dragging the curve around;
5. **screen** gross outliers against a cross-validated robust reference fit;
6. **compare** the bootstrap baseline and the penalised robust spline on a
   maturity-blocked holdout and select one under a fixed, documented rule;
7. **publish** the curve, diagnostics, risk, sensitivity analysis, charts and the
   HTML research report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .cleaning import (
    CleaningConfig,
    CleaningResult,
    apply_exclusions,
    audit_with_weights,
    clean,
    estimate_model_error,
    reweight_instruments,
)
from .curve import DiscountCurve, curve_frame
from .holdout import HoldoutConfig, ModelComparison, compare_models, forward_admissibility
from .instruments import BOND, DEPOSIT, OIS_SWAP, Instrument
from .io import MarketDataError, load_market_data_with_audit
from .models import (
    FitConfig,
    fit_advanced,
    fit_baseline,
    fit_metrics,
    local_residuals,
    residuals_bp,
    screen_outliers,
)
from .pricing import model_quote
from .risk import KEY_TENORS, instrument_risk, verify_dv01
from .sensitivity import SensitivityCheck, curve_shift, leave_block_out, quote_perturbation
from .validation import ValidationConfig, parse_valuation_date, validate

__all__ = ["WorkflowConfig", "WorkflowResult", "run_workflow"]


@dataclass(frozen=True)
class WorkflowConfig:
    grid_points: int = 601
    grid_min_years: float = 1.0 / 12.0
    grid_max_years: float = 30.0
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    fit: FitConfig = field(default_factory=FitConfig)
    holdout: HoldoutConfig = field(default_factory=HoldoutConfig)
    run_sensitivity: bool = True


@dataclass
class WorkflowResult:
    valuation_date: datetime
    market_data_path: Path
    grid: np.ndarray
    curve: DiscountCurve
    curve_table: pd.DataFrame
    comparison: ModelComparison
    cleaning: CleaningResult
    instruments: list[Instrument]
    repricing: pd.DataFrame
    risk: pd.DataFrame
    model_comparison: dict
    sensitivity: dict
    validation_findings: list[str]
    validation_summary: dict
    model_error_bp: dict
    warnings: list[str] = field(default_factory=list)
    #: Timestamp of the freshest observation in the file.  Used as the report's
    #: provenance stamp, so that regenerating the report does not change it.
    market_snapshot: str | None = None


#: The published grid is refined below this maturity.
GRID_REFINEMENT_YEARS = 2.0
#: Share of the grid points spent on the refined front segment.
GRID_FRONT_SHARE = 1.0 / 3.0


def _grid(config: WorkflowConfig) -> np.ndarray:
    """Publication grid: log-spaced to 2Y, then uniform to the horizon.

    A grid that is uniform in ``T`` is far too coarse where the curve actually
    bends.  With 601 uniform points the step is 0.05Y everywhere, and a consumer
    who linearly interpolates ``zero_rate`` between published rows picks up
    0.55bp of error inside the first six months -- larger than the calibration
    residual of every money-market instrument in the file, and entirely an
    artefact of how the curve was *published*.  Spending a third of the rows on a
    geometric grid below 2Y takes that to below 0.001bp while leaving the long
    end (where linear interpolation costs 0.001bp anyway) essentially unchanged.
    """
    if config.grid_points < 361:
        raise ValueError("the output contract requires at least 361 grid rows")
    if config.grid_max_years <= config.grid_min_years:
        raise ValueError("grid_max_years must exceed grid_min_years")
    lo = float(config.grid_min_years)
    hi = float(config.grid_max_years)
    if lo <= 0.0:
        raise ValueError("grid_min_years must be positive")
    split = min(GRID_REFINEMENT_YEARS, hi)
    if split <= lo:
        return np.geomspace(lo, hi, config.grid_points)
    front = max(2, int(round(GRID_FRONT_SHARE * config.grid_points)))
    back = config.grid_points - front + 1
    grid = np.concatenate(
        [
            np.geomspace(lo, split, front)[:-1],
            np.linspace(split, hi, back),
        ]
    )
    grid[0] = lo
    grid[-1] = hi
    return grid


def _fitter(kind: str, config: FitConfig, lam: float | None, power: float | None):
    """Return a callable that refits the selected estimator on a subset."""
    if kind == "advanced":
        def fit(subset: list[Instrument]) -> DiscountCurve:
            return fit_advanced(subset, config, lam=lam, power=power).curve
    else:
        def fit(subset: list[Instrument]) -> DiscountCurve:
            return fit_baseline(subset, config).curve

    return fit


def _repricing_frame(curve: DiscountCurve, instruments: list[Instrument]) -> pd.DataFrame:
    residual_bp = residuals_bp(curve, instruments)
    rows = []
    for inst, bp in zip(instruments, residual_bp):
        model = model_quote(curve, inst)
        rows.append(
            {
                "instrument_id": inst.instrument_id,
                "instrument_type": inst.instrument_type,
                "market_quote": inst.quote,
                "model_quote": model,
                "residual": inst.quote - model,
                "weight": inst.weight,
                "obs_id": inst.obs_id,
                "maturity_years": inst.maturity_years,
                "residual_bp": float(bp),
                "quote_unit": "PRICE_POINTS" if inst.instrument_type == BOND else "PERCENT",
                "half_spread": inst.half_spread,
                "liquidity_score": inst.liquidity_score,
                "source": inst.source,
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values(["maturity_years", "instrument_id"]).reset_index(drop=True)


def _risk_frame(curve: DiscountCurve, instruments: list[Instrument]) -> pd.DataFrame:
    rows = []
    for inst in instruments:
        record = instrument_risk(curve, inst)
        check = verify_dv01(curve, inst)
        row = {
            "instrument_id": record.instrument_id,
            "dv01": record.dv01,
            "key_2y": record.key_rates["key_2y"],
            "key_5y": record.key_rates["key_5y"],
            "key_10y": record.key_rates["key_10y"],
            "key_30y": record.key_rates["key_30y"],
            "instrument_type": record.instrument_type,
            "maturity_years": record.maturity_years,
            "notional": inst.notional(),
            "key_rate_sum": record.key_rate_sum,
            "key_sum_relative_error": record.key_sum_error,
            "dv01_analytic": check["dv01_analytic"],
            "dv01_analytic_relative_error": check["relative_difference"],
        }
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame.sort_values(["maturity_years", "instrument_id"]).reset_index(drop=True)


def _model_comparison_payload(
    comparison: ModelComparison, model_error_bp: dict, warnings: list[str]
) -> dict:
    split = comparison.split
    advanced = comparison.advanced_full
    baseline = comparison.baseline_full
    train_lambda = (
        comparison.advanced_train.smoothing_lambda if comparison.advanced_train else None
    )
    return {
        "holdout": {
            "method": split.method,
            "n_blocks": len(split.blocks),
            "n_train": len(split.train),
            "n_holdout": len(split.holdout),
            "holdout_block_indices": split.holdout_blocks,
            "holdout_maturity_ranges": [
                list(split.block_maturities[b]) for b in split.holdout_blocks
            ],
            "notes": split.notes,
        },
        "baseline": {
            "name": baseline.name,
            "description": baseline.description,
            "n_pillars": len(baseline.pillars),
            "skipped_pillars": baseline.skipped,
            "train_metrics": comparison.metrics["train"].get("baseline", {}),
            "holdout_metrics": comparison.metrics["holdout"].get("baseline", {}),
            "full_sample_metrics": comparison.metrics["full_sample"]["baseline"],
            "forward_roughness": comparison.metrics["forward_roughness"]["baseline"],
            "forward_admissibility": comparison.metrics["forward_admissibility"]["baseline"],
            "notes": baseline.notes,
        },
        "advanced": {
            "name": advanced.name,
            "description": advanced.description,
            "n_knots": int(advanced.knots.size),
            "knots": [float(k) for k in advanced.knots],
            "smoothing_lambda": advanced.smoothing_lambda,
            "penalty_maturity_power": advanced.penalty_power,
            "smoothing_lambda_train_split": train_lambda,
            "cross_validation_scores_bp": advanced.cv_scores,
            "irls_iterations": advanced.iterations,
            "irls_converged": advanced.converged,
            "robust_scale_bp": advanced.robust_scale_bp,
            "n_zero_robust_weight": int(np.sum(advanced.robust_weights <= 0.0)),
            "train_metrics": comparison.metrics["train"].get("advanced", {}),
            "holdout_metrics": comparison.metrics["holdout"].get("advanced", {}),
            "full_sample_metrics": comparison.metrics["full_sample"]["advanced"],
            "forward_roughness": comparison.metrics["forward_roughness"]["advanced"],
            "forward_admissibility": comparison.metrics["forward_admissibility"]["advanced"],
            "notes": advanced.notes,
        },
        # ``selected_model`` is the mandated top-level key; ``model_selected`` is
        # kept as an alias so an existing consumer of round 1 does not break.
        "selected_model": comparison.selected,
        "model_selected": comparison.selected,
        "metric_units": {
            "weighted_rmse_bp": "basis points, yield-equivalent, weighted by the "
                                "calibration weight",
            "rmse_bp": "basis points, yield-equivalent, unweighted",
            "mae_bp": "basis points, yield-equivalent, unweighted",
            "median_abs_bp": "basis points, yield-equivalent",
            "max_abs_bp": "basis points, yield-equivalent",
            "forward_roughness": "mean squared second derivative of the "
                                 "instantaneous forward, (1/year^2)^2",
            "smoothing_lambda": "bp^2 per year^3 (roughness weight)",
        },
        "selection_rule": (
            "1) reject any curve whose instantaneous forward leaves the quoted rate "
            "range by more than the admissibility tolerance; 2) among admissible "
            "curves take the lower maturity-blocked holdout weighted RMSE, requiring "
            "the advanced estimator to beat the baseline by the parsimony margin "
            "before its extra complexity is accepted"
        ),
        "selection_rationale": comparison.rationale,
        "estimated_model_error_bp": model_error_bp,
        "warnings": warnings,
    }


#: One sentence per experiment saying what the number means.  Kept next to the
#: payload builder so a new experiment cannot be added without one.
_INTERPRETATION = {
    "bid_ask_repricing":
        "Refitting entirely on bid and entirely on ask moves the curve by at most "
        "{value:.2f}bp, so the observable two-way market supports the level to "
        "about that width.",
    "smoothing_strength":
        "Moving the roughness weight one grid step either side of the "
        "cross-validated choice moves the curve by at most {value:.2f}bp; that is "
        "the cost of the smoothing decision itself.",
    "outlier_exclusion_policy":
        "Reinstating every screened observation moves the curve by at most "
        "{value:.2f}bp, which bounds how much the exclusion policy is doing.",
    "leave_one_block_out_stability":
        "Dropping any single maturity block moves the curve by at most "
        "{value:.2f}bp; the worst block is where the data, not the model, is "
        "holding the curve up.",
    "single_quote_one_bp_perturbation":
        "A one-basis-point move in the most heavily weighted quote propagates at "
        "most {value:.2f}bp, so no single observation dominates the fit.",
    "model_choice_dispersion":
        "The two candidate estimators differ by at most {value:.2f}bp on the "
        "published grid: the part of the answer that is a modelling choice rather "
        "than market data.",
}


def _sensitivity_payload(
    result_curve: DiscountCurve,
    instruments: list[Instrument],
    pre_screen_instruments: list[Instrument],
    bid_instruments: list[Instrument],
    ask_instruments: list[Instrument],
    comparison: ModelComparison,
    config: WorkflowConfig,
    grid: np.ndarray,
) -> dict:
    kind = comparison.selected
    advanced = comparison.advanced_full
    lam = advanced.smoothing_lambda if kind == "advanced" else None
    power = advanced.penalty_power if kind == "advanced" else None
    fit = _fitter(kind, config.fit, lam, power)
    checks: list[SensitivityCheck] = []

    # 1. two-way market: refit on bid quotes and on ask quotes.
    bid_curve = fit(bid_instruments)
    ask_curve = fit(ask_instruments)
    bid_stats = curve_shift(result_curve, bid_curve, grid)
    ask_stats = curve_shift(result_curve, ask_curve, grid)
    checks.append(
        SensitivityCheck(
            name="bid_ask_repricing",
            description=(
                "refit the selected estimator entirely on bid quotes and entirely on "
                "ask quotes; the span brackets the curve that the observable two-way "
                "market can support"
            ),
            metric="max_abs_zero_shift_bp",
            value=float(max(bid_stats["max_abs_bp"], ask_stats["max_abs_bp"])),
            detail={"bid_side": bid_stats, "ask_side": ask_stats},
        )
    )

    # 2. smoothing strength.
    if kind == "advanced":
        softer = _fitter(kind, config.fit, lam * 0.1, power)(instruments)
        stiffer = _fitter(kind, config.fit, lam * 10.0, power)(instruments)
        soft_stats = curve_shift(result_curve, softer, grid)
        stiff_stats = curve_shift(result_curve, stiffer, grid)
        value = float(max(soft_stats["max_abs_bp"], stiff_stats["max_abs_bp"]))
        detail = {
            "selected_lambda": lam,
            "lambda_over_ten": soft_stats,
            "lambda_times_ten": stiff_stats,
        }
    else:
        merged = _fitter(
            kind,
            FitConfig(**{**config.fit.__dict__, "min_pillar_gap_years": 0.25}),
            None,
            None,
        )(instruments)
        stats = curve_shift(result_curve, merged, grid)
        value = float(stats["max_abs_bp"])
        detail = {"min_pillar_gap_years": 0.25, "shift": stats}
    checks.append(
        SensitivityCheck(
            name="smoothing_strength",
            description=(
                "move the selected smoothing control by a factor of ten in each "
                "direction and measure how far the published zero curve travels"
                if kind == "advanced"
                else "widen the minimum bootstrap pillar spacing and measure how far "
                "the published zero curve travels"
            ),
            metric="max_abs_zero_shift_bp",
            value=value,
            detail=detail,
        )
    )

    # 3. outlier-exclusion policy.
    reinstated = fit(pre_screen_instruments)
    stats = curve_shift(result_curve, reinstated, grid)
    checks.append(
        SensitivityCheck(
            name="outlier_exclusion_policy",
            description=(
                "refit with every screened observation reinstated (robust reweighting "
                "still active) to show how much of the published curve depends on the "
                "exclusion decisions rather than on the robust estimator"
            ),
            metric="max_abs_zero_shift_bp",
            value=float(stats["max_abs_bp"]),
            detail={
                "n_reinstated": len(pre_screen_instruments) - len(instruments),
                "shift": stats,
            },
        )
    )

    # 4. leave-one-maturity-block-out stability.
    stability = leave_block_out(
        instruments, comparison.split.blocks, fit, result_curve, grid
    )
    checks.append(
        SensitivityCheck(
            name="leave_one_block_out_stability",
            description=(
                "drop one maturity block of quotes at a time and refit; the worst "
                "resulting shift bounds how much any single maturity region is holding "
                "the published curve in place"
            ),
            metric="worst_max_abs_zero_shift_bp",
            value=float(stability.get("worst_max_abs_bp", float("nan"))),
            detail=stability,
        )
    )

    # 5. single-quote perturbation.
    perturbation = quote_perturbation(instruments, fit, result_curve, grid)
    checks.append(
        SensitivityCheck(
            name="single_quote_one_bp_perturbation",
            description=(
                "move the most heavily weighted quote near 10Y by one basis point and "
                "measure how far the shock propagates along the curve"
            ),
            metric="max_abs_zero_shift_bp",
            value=float(perturbation.get("max_abs_bp", float("nan"))),
            detail=perturbation,
        )
    )

    # 6. cross-model dispersion.
    other = (
        comparison.baseline_full.curve
        if kind == "advanced"
        else comparison.advanced_full.curve
    )
    stats = curve_shift(result_curve, other, grid)
    checks.append(
        SensitivityCheck(
            name="model_choice_dispersion",
            description=(
                "difference between the two estimators on the published grid: the part "
                "of the answer that is a modelling choice rather than market data"
            ),
            metric="max_abs_zero_shift_bp",
            value=float(stats["max_abs_bp"]),
            detail=stats,
        )
    )

    # Each experiment is also promoted to a NAMED TOP-LEVEL KEY carrying its
    # condition, its numeric result and its interpretation, so a consumer can
    # address one experiment without walking a list.  ``checks`` is retained as
    # the ordered view of the same objects.
    payload = {
        "grid_min_years": float(grid[0]),
        "grid_max_years": float(grid[-1]),
        "selected_model": kind,
        "experiment_names": [c.name for c in checks],
        "checks": [c.as_dict() for c in checks],
    }
    for check in checks:
        payload[check.name] = {
            "condition": check.description,
            "result": {
                "metric": check.metric,
                "value": check.value,
                "unit": "bp of continuously compounded zero rate on the "
                        "published grid",
                "detail": check.detail,
            },
            "interpretation": _INTERPRETATION.get(check.name, "").format(
                value=check.value
            ),
        }
    return payload


def _side_instruments(instruments: list[Instrument], side: str) -> list[Instrument]:
    """Instruments requoted at the bid or the ask side of their own market."""
    out: list[Instrument] = []
    for inst in instruments:
        if inst.half_spread <= 0:
            out.append(inst)
            continue
        shift = -inst.half_spread if side == "bid" else inst.half_spread
        out.append(
            Instrument(
                obs_id=inst.obs_id,
                instrument_id=inst.instrument_id,
                instrument_type=inst.instrument_type,
                maturity_years=inst.maturity_years,
                coupon_rate=inst.coupon_rate,
                payment_frequency=inst.payment_frequency,
                quote=inst.quote + shift,
                half_spread=inst.half_spread,
                liquidity_score=inst.liquidity_score,
                weight=inst.weight,
                source=inst.source,
                timestamp=inst.timestamp,
                quality_factor=inst.quality_factor,
                sigma_quote_bp=inst.sigma_quote_bp,
                notes=inst.notes,
            )
        )
    return out


def run_workflow(
    market_data: str | Path,
    valuation_date: str | datetime,
    config: WorkflowConfig | None = None,
) -> WorkflowResult:
    """Run the complete research workflow and return every artefact in memory."""
    config = config or WorkflowConfig()
    value_date = (
        valuation_date
        if isinstance(valuation_date, datetime)
        else parse_valuation_date(valuation_date)
    )
    path = Path(market_data)
    loaded = load_market_data_with_audit(path)
    report = validate(loaded, value_date, config.validation)
    cleaned = clean(loaded, report, value_date, config.cleaning, config.validation)
    warnings: list[str] = []

    if len(cleaned.instruments) < 2:
        raise MarketDataError(
            f"only {len(cleaned.instruments)} usable observation(s) survived validation; "
            "at least two are required to build a curve. Inspect diagnostics/cleaning.csv "
            "for the reason attached to each rejected row."
        )

    # -- error model -----------------------------------------------------
    # A first flexible robust fit supplies the residual dispersion per instrument
    # type.  The *raw* residual scale is the right input here: it measures how
    # closely a single discount curve can actually reprice that instrument type,
    # which is exactly the uncertainty the calibration weights should carry.
    preliminary = fit_advanced(
        cleaned.instruments,
        config.fit,
        lam=config.fit.screening_lambda,
        power=config.fit.screening_power,
    )
    model_error = estimate_model_error(
        cleaned.instruments,
        residuals_bp(preliminary.curve, cleaned.instruments),
        config.cleaning,
    )
    weighted = reweight_instruments(cleaned.instruments, model_error, config.cleaning)

    # -- outlier screen ---------------------------------------------------
    reasons, _ = screen_outliers(weighted, config.fit)
    cleaned = CleaningResult(
        instruments=weighted,
        audit=audit_with_weights(cleaned.audit, weighted),
        findings=cleaned.findings,
        summary=cleaned.summary,
    )
    pre_screen = list(weighted)
    cleaned = apply_exclusions(cleaned, reasons)
    instruments = cleaned.instruments
    if len(instruments) < 2:
        raise MarketDataError(
            "the robust outlier screen left fewer than two usable instruments; the "
            "quote set is not internally consistent enough to calibrate a curve"
        )

    # -- model comparison and selection -----------------------------------
    comparison = compare_models(instruments, config.fit, config.holdout)
    curve = comparison.selected_curve
    grid = _grid(config)
    frame = curve_frame(curve, grid)
    curve_table = pd.DataFrame(
        {
            "maturity_years": frame["maturity_years"],
            "zero_rate": frame["zero_rate"],
            "discount_factor": frame["discount_factor"],
            "forward_rate": frame["forward_rate"],
        }
    )
    if not np.all(np.isfinite(curve_table.to_numpy())):
        raise MarketDataError("the calibrated curve contains non-finite values")
    if float(curve_table["discount_factor"].min()) <= 0.0:
        raise MarketDataError("the calibrated curve produced a non-positive discount factor")

    horizon = float(max(i.maturity_years for i in instruments))
    if grid[-1] > horizon:
        warnings.append(
            f"the published grid extends to {grid[-1]:.2f}Y but the longest usable "
            f"instrument matures at {horizon:.2f}Y; beyond that point the curve holds "
            "the instantaneous forward flat and carries no market information"
        )
    if not comparison.split.usable:
        warnings.append(
            "no maturity-blocked holdout could be formed; the model comparison rests "
            "on in-sample metrics and the forward-admissibility gate alone"
        )

    repricing = _repricing_frame(curve, instruments)
    risk = _risk_frame(curve, instruments)
    worst_key = float(np.max(np.abs(risk["key_sum_relative_error"]))) if len(risk) else 0.0
    worst_dv01 = (
        float(np.max(np.abs(risk["dv01_analytic_relative_error"]))) if len(risk) else 0.0
    )
    if worst_key > 1.0e-3:
        warnings.append(
            f"key-rate sensitivities do not add back to the parallel DV01 within 0.1% "
            f"(worst {worst_key:.2e})"
        )
    if worst_dv01 > 1.0e-4:
        warnings.append(
            f"finite-difference DV01 differs from the analytic derivative by more than "
            f"1e-4 relative (worst {worst_dv01:.2e})"
        )

    payload = _model_comparison_payload(comparison, model_error, warnings)
    sensitivity: dict = {"checks": []}
    if config.run_sensitivity:
        sensitivity = _sensitivity_payload(
            curve,
            instruments,
            pre_screen,
            _side_instruments(instruments, "bid"),
            _side_instruments(instruments, "ask"),
            comparison,
            config,
            grid,
        )

    return WorkflowResult(
        valuation_date=value_date,
        market_data_path=path,
        grid=grid,
        curve=curve,
        curve_table=curve_table,
        comparison=comparison,
        cleaning=cleaned,
        instruments=instruments,
        repricing=repricing,
        risk=risk,
        model_comparison=payload,
        sensitivity=sensitivity,
        validation_findings=report.findings,
        validation_summary=report.summary,
        model_error_bp=model_error,
        warnings=warnings,
        market_snapshot=(
            None
            if report.latest_timestamp is None
            else report.latest_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
    )
