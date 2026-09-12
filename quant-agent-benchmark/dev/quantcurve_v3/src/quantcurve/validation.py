"""Holdout validation: maturity-grouped K-fold and a time-aware split."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .advanced import AdvancedConfig, fit_advanced
from .baseline import fit_baseline
from .instruments import Instrument
from .pricing import model_quote, rate_residual


def _metrics(err_bp: np.ndarray, precision: np.ndarray | None = None) -> dict:
    """RMSE/MAE/max plus a precision-weighted RMSE (weights = base precision 1/scale^2).

    The weighted RMSE is the primary comparison metric: it is not dominated by
    a single illiquid quote with a 50bp bid/ask spread, and it mirrors the
    information content the fitting objective assigns to each quote.
    """
    if len(err_bp) == 0:
        return {"n": 0, "rmse_bp": None, "weighted_rmse_bp": None, "mae_bp": None, "median_abs_bp": None, "max_abs_bp": None}
    out = {
        "n": int(len(err_bp)),
        "rmse_bp": float(np.sqrt(np.mean(err_bp**2))),
        "weighted_rmse_bp": None,
        "mae_bp": float(np.mean(np.abs(err_bp))),
        "median_abs_bp": float(np.median(np.abs(err_bp))),
        "max_abs_bp": float(np.max(np.abs(err_bp))),
    }
    if precision is not None and np.sum(precision) > 0:
        out["weighted_rmse_bp"] = float(np.sqrt(np.sum(precision * err_bp**2) / np.sum(precision)))
    return out


def summarize_errors(frame: pd.DataFrame, column: str, precision_column: str | None = "precision") -> dict:
    prec = frame[precision_column].to_numpy(dtype=float) if precision_column and precision_column in frame else None
    out = {"overall": _metrics(frame[column].to_numpy(dtype=float), prec)}
    out["by_type"] = {}
    for t, g in frame.groupby("instrument_type"):
        pg = g[precision_column].to_numpy(dtype=float) if prec is not None else None
        out["by_type"][t] = _metrics(g[column].to_numpy(dtype=float), pg)
    return out


@dataclass
class HoldoutResult:
    predictions: pd.DataFrame
    metrics: dict
    per_fold: pd.DataFrame
    temporal: dict


def run_grouped_holdout(
    instruments: list[Instrument],
    table: pd.DataFrame,
    base_scale: np.ndarray,
    final_factor: np.ndarray,
    final_weights: np.ndarray,
    cluster_ids: np.ndarray,
    folds: np.ndarray,
    cfg: AdvancedConfig,
    lam: float,
    power: float,
    knots: np.ndarray,
    t_max: float,
) -> HoldoutResult:
    """Refit both models on each training fold and score the held-out clusters.

    Held-out instruments that the full-data robust fit excluded (final robust
    factor zero) are not scored: they are data errors, not test cases.
    """
    types = table["instrument_type"].to_numpy()
    rows = []
    fold_rows = []
    fold_ids = sorted(set(int(f) for f in folds if f >= 0))
    for f in fold_ids:
        train = folds != f
        test = (folds == f) & (final_factor > 0)
        if test.sum() == 0:
            continue
        train_insts = [i for i, m in zip(instruments, train) if m]
        base_curve = fit_baseline(train_insts, final_weights[train], cluster_ids[train])
        adv = fit_advanced(train_insts, base_scale[train], types[train], cluster_ids[train], t_max, cfg, lam=lam, power=power, knots=knots, run_cv=False)
        fold_err = {"fold": f, "n_test": int(test.sum())}
        errs_b, errs_a = [], []
        for j in np.flatnonzero(test):
            inst = instruments[j]
            eb = -rate_residual(inst, base_curve) * 1e4
            ea = -rate_residual(inst, adv.curve) * 1e4
            errs_b.append(eb)
            errs_a.append(ea)
            rows.append(
                {
                    "instrument_id": inst.instrument_id,
                    "instrument_type": inst.instrument_type,
                    "maturity_years": inst.maturity,
                    "fold": f,
                    "market_quote": inst.quote * (1.0 if inst.instrument_type == "bond" else 100.0),
                    "baseline_quote": model_quote(inst, base_curve) * (1.0 if inst.instrument_type == "bond" else 100.0),
                    "advanced_quote": model_quote(inst, adv.curve) * (1.0 if inst.instrument_type == "bond" else 100.0),
                    "baseline_error_bp": eb,
                    "advanced_error_bp": ea,
                    "precision": float(1.0 / base_scale[j] ** 2),
                }
            )
        fold_err["baseline_rmse_bp"] = float(np.sqrt(np.mean(np.square(errs_b))))
        fold_err["advanced_rmse_bp"] = float(np.sqrt(np.mean(np.square(errs_a))))
        fold_rows.append(fold_err)
    predictions = pd.DataFrame(rows)
    band = np.where(predictions["maturity_years"] <= 2.0, "short_T<=2", np.where(predictions["maturity_years"] < 15.0, "mid_2<T<15", "long_T>=15"))
    predictions["tenor_band"] = band
    metrics = {
        "baseline": summarize_errors(predictions, "baseline_error_bp"),
        "advanced": summarize_errors(predictions, "advanced_error_bp"),
        "units": "yield-equivalent basis points, market minus model (bond price errors divided by dollar duration); weighted metrics use precision 1/base_scale^2",
    }
    temporal = run_temporal_holdout(instruments, table, base_scale, final_factor, final_weights, cluster_ids, cfg, lam, power, knots, t_max)
    for model, col in (("baseline", "baseline_error_bp"), ("advanced", "advanced_error_bp")):
        bands = {}
        for b in ("short_T<=2", "mid_2<T<15", "long_T>=15"):
            sub = predictions[predictions["tenor_band"] == b]
            bands[b] = summarize_errors(sub, col)["overall"] if len(sub) else {"n": 0, "note": "no held-out instruments in this band (missing, not zero error)"}
        metrics[model]["by_tenor_band"] = bands
    return HoldoutResult(predictions=predictions, metrics=metrics, per_fold=pd.DataFrame(fold_rows), temporal=temporal)


def run_temporal_holdout(
    instruments: list[Instrument],
    table: pd.DataFrame,
    base_scale: np.ndarray,
    final_factor: np.ndarray,
    final_weights: np.ndarray,
    cluster_ids: np.ndarray,
    cfg: AdvancedConfig,
    lam: float,
    power: float,
    knots: np.ndarray,
    t_max: float,
) -> dict:
    """Time-aware split: fit on the earlier half of the quote timestamps, score the later half.

    Same tenors appear on both sides, so this measures consistency with later
    quotes (noise level) rather than interpolation skill.
    """
    ts = pd.to_datetime(table["timestamp"], utc=True, errors="coerce")
    usable = final_factor > 0
    if ts.isna().all() or usable.sum() < 10:
        return {"available": False, "reason": "timestamps unavailable or too few usable instruments"}
    cutoff = ts[usable].median()
    train = (ts <= cutoff).to_numpy() & usable
    test = (ts > cutoff).to_numpy() & usable
    types = table["instrument_type"].to_numpy()
    if train.sum() < 8 or test.sum() < 4 or not np.isin(["deposit", "ois_swap"], types[train]).any():
        return {"available": False, "reason": "temporal split too unbalanced"}
    train_insts = [i for i, m in zip(instruments, train) if m]
    try:
        base_curve = fit_baseline(train_insts, final_weights[train], cluster_ids[train])
        adv = fit_advanced(train_insts, base_scale[train], types[train], cluster_ids[train], t_max, cfg, lam=lam, power=power, knots=knots, run_cv=False)
    except ValueError as exc:
        return {"available": False, "reason": f"temporal split not fittable: {exc}"}
    frame = pd.DataFrame(
        {
            "instrument_type": types[test],
            "baseline_error_bp": [-rate_residual(instruments[j], base_curve) * 1e4 for j in np.flatnonzero(test)],
            "advanced_error_bp": [-rate_residual(instruments[j], adv.curve) * 1e4 for j in np.flatnonzero(test)],
            "precision": 1.0 / base_scale[test] ** 2,
        }
    )
    return {
        "available": True,
        "cutoff_timestamp": str(cutoff),
        "n_train": int(train.sum()),
        "n_test": int(test.sum()),
        "baseline": summarize_errors(frame, "baseline_error_bp"),
        "advanced": summarize_errors(frame, "advanced_error_bp"),
    }
