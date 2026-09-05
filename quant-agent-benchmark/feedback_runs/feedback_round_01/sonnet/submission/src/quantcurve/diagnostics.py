"""Repricing diagnostics, model comparison, and sensitivity/stability checks."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .calibration import (
    FINE_GRID,
    active_knots,
    fit_advanced,
    fit_baseline,
    model_quote,
    weighted_rmse,
)
from .grids import CALIBRATION_KNOTS, KEY_RATE_POINTS
from .risk import dv01


def repricing_table(df_usable: pd.DataFrame, discount_fn) -> pd.DataFrame:
    rows = []
    for r in df_usable.itertuples():
        model = model_quote(r, discount_fn)
        rows.append(
            {
                "instrument_id": r.instrument_id,
                "instrument_type": r.instrument_type,
                "market_quote": r.normalized_quote,
                "model_quote": model,
                "residual": r.normalized_quote - model,
                "weight": r.weight,
                "split": getattr(r, "split", "train"),
                "action": r.action,
            }
        )
    return pd.DataFrame(rows)


def model_comparison_payload(
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    baseline_fit,
    advanced_fit,
    best_lambda: float,
    selected: str,
    rationale: str,
) -> dict:
    from .calibration import per_type_rmse

    return {
        "baseline": {
            "train_weighted_rmse": weighted_rmse(train, baseline_fit.curve.discount, baseline_fit.per_type_scale),
            "holdout_weighted_rmse": weighted_rmse(holdout, baseline_fit.curve.discount, baseline_fit.per_type_scale),
            "train_rmse_by_type": per_type_rmse(train, baseline_fit.curve.discount),
            "holdout_rmse_by_type": per_type_rmse(holdout, baseline_fit.curve.discount),
        },
        "advanced": {
            "lambda_regularization": best_lambda,
            "train_weighted_rmse": weighted_rmse(train, advanced_fit.curve.discount, baseline_fit.per_type_scale),
            "holdout_weighted_rmse": weighted_rmse(holdout, advanced_fit.curve.discount, baseline_fit.per_type_scale),
            "train_rmse_by_type": per_type_rmse(train, advanced_fit.curve.discount),
            "holdout_rmse_by_type": per_type_rmse(holdout, advanced_fit.curve.discount),
            "n_irls_iterations": len(advanced_fit.irls_history),
            "irls_downweight_history": advanced_fit.irls_history,
        },
        "model_selected": selected,
        "selected_model": selected,
        "selection_rationale": rationale,
    }


def _representative_instruments(df_usable: pd.DataFrame, n_per_type: int = 3) -> pd.DataFrame:
    parts = []
    for _, sub in df_usable.groupby("instrument_type"):
        idx = np.linspace(0, len(sub) - 1, min(n_per_type, len(sub))).round().astype(int)
        parts.append(sub.iloc[np.unique(idx)])
    return pd.concat(parts)


def bump_size_convergence_check(df_usable: pd.DataFrame, curve) -> dict:
    """DV01 is *defined* (CONVENTIONS.md) as the PV move for a 1bp bump, so the
    raw finite-difference value scales linearly with whatever bump size is
    used -- that is expected, not noise. To check that the reported 1bp DV01
    is a good estimate of the true local derivative (i.e. the instrument is
    close enough to linear over this range that the estimate has converged),
    each raw value is rescaled to a common "per 1bp" basis before comparing.
    """
    sample = _representative_instruments(df_usable)
    raw = {}
    normalized = {}
    for bump in (0.001, 0.0001, 0.00001):
        vals = [dv01(row, curve, bump=bump) for row in sample.itertuples()]
        raw[f"bump_{bump:g}"] = float(np.mean(np.abs(vals)))
        normalized[f"bump_{bump:g}"] = raw[f"bump_{bump:g}"] * (0.0001 / bump)
    ref = normalized["bump_0.0001"]
    rel_diff_10bp = abs(normalized["bump_0.001"] - ref) / max(abs(ref), 1e-9)
    rel_diff_0p1bp = abs(normalized["bump_1e-05"] - ref) / max(abs(ref), 1e-9)
    return {
        "description": "Mean |DV01| across a representative instrument sample at three finite-difference "
        "step sizes (10bp, 1bp, 0.1bp), each rescaled to a common per-1bp basis (DV01 scales linearly "
        "with bump size by definition, so raw values are not directly comparable); the rescaled estimate "
        "should be stable if the 1bp DV01 is a good local-derivative approximation.",
        "mean_abs_dv01_by_bump_raw": raw,
        "mean_abs_dv01_by_bump_per_1bp": normalized,
        "relative_diff_10bp_vs_1bp": rel_diff_10bp,
        "relative_diff_0p1bp_vs_1bp": rel_diff_0p1bp,
        "stable": bool(rel_diff_10bp < 0.05 and rel_diff_0p1bp < 0.05),
    }


def regularization_sensitivity_check(grid_results: list[dict]) -> dict:
    return {
        "description": "Advanced-model holdout weighted RMSE across the smoothing-strength (lambda) grid "
        "searched during model selection.",
        "grid": grid_results,
    }


def leave_worst_out_refit_check(train: pd.DataFrame, per_type_scale: dict, knots: np.ndarray) -> dict:
    base_full = fit_baseline(train, knots=knots)
    rows = list(train.itertuples())
    residuals = np.array(
        [
            abs(r.normalized_quote - model_quote(r, base_full.curve.discount)) * r.weight / per_type_scale[r.instrument_type]
            for r in rows
        ]
    )
    worst_pos = int(np.argmax(residuals))
    worst_id = rows[worst_pos].instrument_id
    reduced = train.drop(train.index[worst_pos])

    base_reduced = fit_baseline(reduced, knots=knots)

    probe_points = np.array([2.0, 5.0, 10.0, 30.0])
    probe_points = probe_points[(probe_points >= knots[0]) & (probe_points <= knots[-1])]
    z_full = base_full.curve.zero_rate(probe_points)
    z_reduced = base_reduced.curve.zero_rate(probe_points)
    max_shift_bp = float(np.max(np.abs(z_full - z_reduced)) * 1e4)

    return {
        "description": "Baseline curve stability when the single largest-residual training instrument is "
        "removed and the model is refit (a leave-one-out influence check).",
        "removed_instrument_id": worst_id,
        "probe_maturities": probe_points.tolist(),
        "max_zero_rate_shift_bp": max_shift_bp,
        "stable": bool(max_shift_bp < 10.0),
    }


def negative_rate_stress_check(train: pd.DataFrame, per_type_scale: dict, knots: np.ndarray, shock_pct_points: float = 3.0) -> dict:
    shocked = train.copy()
    rate_mask = shocked["instrument_type"].isin(["deposit", "ois_swap"])
    shocked.loc[rate_mask, "normalized_quote"] = shocked.loc[rate_mask, "normalized_quote"] - shock_pct_points

    fit = fit_baseline(shocked, knots=knots)
    grid = np.linspace(knots[0], knots[-1], 200)
    zero_rates_on_grid = fit.curve.zero_rate(grid)
    discounts_on_grid = fit.curve.discount(grid)

    return {
        "description": f"All deposit/swap quotes parallel-shocked down by {shock_pct_points:g} percentage "
        "points and the baseline curve refit, to confirm negative zero rates are supported "
        "without discount factors falling to or below zero.",
        "min_zero_rate": float(np.min(zero_rates_on_grid)),
        "fraction_of_grid_negative": float(np.mean(zero_rates_on_grid < 0.0)),
        "min_discount_factor": float(np.min(discounts_on_grid)),
        "all_discount_factors_positive": bool(np.all(discounts_on_grid > 0.0)),
    }


def forward_smoothness_check(baseline_curve, advanced_curve, knots: np.ndarray, eps: float = 1e-4) -> dict:
    """Forward-rate error is not the same diagnostic as zero-rate error:
    f(t) = z(t) + t*z'(t) amplifies any slope discontinuity in z(t) by a
    factor of t. A piecewise-linear zero curve (baseline) has a *kinked*
    z(t), so f(t) is discontinuous at every internal knot by construction;
    a natural-cubic-spline zero curve (advanced) is C1, so f(t) should stay
    continuous there. This reports the actual size of that jump at each
    internal knot for both fitted curves, so the two error types are
    visible separately instead of only a single blended repricing RMSE.
    """
    internal = knots[1:-1]
    rows = []
    for k in internal:
        f_base_left = float(baseline_curve.forward_rate(k - eps))
        f_base_right = float(baseline_curve.forward_rate(k + eps))
        f_adv_left = float(advanced_curve.forward_rate(k - eps))
        f_adv_right = float(advanced_curve.forward_rate(k + eps))
        rows.append(
            {
                "knot": float(k),
                "baseline_jump_bp": abs(f_base_right - f_base_left) * 1e4,
                "advanced_jump_bp": abs(f_adv_right - f_adv_left) * 1e4,
            }
        )
    baseline_jumps = [r["baseline_jump_bp"] for r in rows]
    advanced_jumps = [r["advanced_jump_bp"] for r in rows]
    worst = max(rows, key=lambda r: r["baseline_jump_bp"]) if rows else None
    return {
        "description": "Forward rate f(t)=z(t)+t*z'(t) jump at each internal calibration knot, evaluated "
        f"just below/above the knot (eps={eps:g}y), for the baseline (piecewise-linear zero, expected to "
        "show real jumps at knots where the local slope changes sharply) and the advanced (natural-cubic-"
        "spline zero, expected to stay ~continuous) curves. This is a distinct diagnostic from zero-rate "
        "repricing RMSE: a curve can reprice deposits/swaps/bonds well (small zero-rate error) while still "
        "producing large, economically implausible forward-rate jumps in a noisy or tightly-clustered "
        "calibration region.",
        "per_knot": rows,
        "baseline_max_jump_bp": max(baseline_jumps) if baseline_jumps else None,
        "baseline_mean_jump_bp": float(np.mean(baseline_jumps)) if baseline_jumps else None,
        "advanced_max_jump_bp": max(advanced_jumps) if advanced_jumps else None,
        "advanced_mean_jump_bp": float(np.mean(advanced_jumps)) if advanced_jumps else None,
        "worst_baseline_knot": worst,
    }


def build_sensitivity_report(
    train: pd.DataFrame,
    df_usable: pd.DataFrame,
    curve,
    per_type_scale: dict,
    knots_train: np.ndarray,
    lambda_grid_results: list[dict],
) -> dict:
    return {
        "bump_size_convergence": bump_size_convergence_check(df_usable, curve),
        "regularization_sensitivity": regularization_sensitivity_check(lambda_grid_results),
        "leave_worst_out_refit": leave_worst_out_refit_check(train, per_type_scale, knots_train),
        "negative_rate_stress": negative_rate_stress_check(train, per_type_scale, knots_train),
    }
