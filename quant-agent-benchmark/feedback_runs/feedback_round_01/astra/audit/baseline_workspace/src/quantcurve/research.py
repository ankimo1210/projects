"""Visible grouped validation, fixed perturbation studies, and model selection."""
from __future__ import annotations

import numpy as np

from .config import Config
from .fitting import fit_curve
from .pricing import PricingEngine


def maturity_groups(frame):
    """Common buckets across instrument types prevent same/near-tenor leakage."""
    t = frame.maturity_years.to_numpy(float)
    labels = []
    for value in t:
        width = 0.25 if value < 2 else (1.0 if value < 10 else 2.0)
        region = 0 if value < 2 else (1 if value < 10 else 2)
        labels.append(f"{region}:{int(np.floor(value / width + 0.5))}")
    return np.array(labels)


def holdout_mask(frame):
    groups = maturity_groups(frame)
    ordered = list(dict.fromkeys(groups[np.argsort(frame.maturity_years.to_numpy(), kind="stable")]))
    # Endpoint buckets stay in training; use deterministic dispersed interior
    # buckets, not a random instrument split or observation-ID-based split.
    chosen = ordered[2:-1:5]
    if not chosen:
        chosen = ordered[1:2]
    mask = np.isin(groups, chosen)
    if mask.sum() < 2 or (~mask).sum() < 6:
        raise ValueError("insufficient maturity-group coverage for defensible holdout validation")
    return mask


def metrics(frame, predictions):
    residual = np.asarray(predictions) - frame.normalized_quote.to_numpy(float)
    scaled = residual / frame.sigma.to_numpy(float)
    weights = frame.reliability.to_numpy(float)
    absolute = abs(scaled)
    delta = 2.5
    loss = np.where(absolute <= delta, scaled**2, 2 * delta * absolute - delta**2)
    out = {"n": len(frame), "weighted_huber_loss": float(np.average(loss, weights=weights)),
           "standardized_rmse": float(np.sqrt(np.average(scaled**2, weights=weights))),
           "median_absolute_standardized_error": float(np.median(absolute)),
           "within_bid_ask_fraction": float(np.mean((predictions >= frame.normalized_bid) & (predictions <= frame.normalized_ask))),
           "by_instrument_type": {}}
    for typ in ("deposit", "ois_swap", "bond"):
        m = frame.instrument_type.to_numpy() == typ
        if not m.any():
            continue
        multiplier = 1.0 if typ == "bond" else 1e4
        e = residual[m] * multiplier
        out["by_instrument_type"][typ] = {"n": int(m.sum()), "units": "price points per 100" if typ == "bond" else "rate basis points",
                                               "rmse": float(np.sqrt(np.mean(e**2))), "median_absolute_error": float(np.median(abs(e))),
                                               "mean_signed_error": float(np.mean(e))}
    return out


def compare_models(frame, config=Config()):
    holdout = holdout_mask(frame)
    train = frame.loc[~holdout].reset_index(drop=True)
    test = frame.loc[holdout].reset_index(drop=True)
    groups = maturity_groups(train)
    ordered = list(dict.fromkeys(groups))
    group_fold = {group: i % 3 for i, group in enumerate(ordered)}
    folds = np.array([group_fold[g] for g in groups])
    tuning = []
    for lam in config.smoothing_candidates:
        scores = []
        for fold in range(3):
            mask = folds == fold
            if mask.sum() == 0 or (~mask).sum() < 6:
                continue
            sub = train.loc[~mask].reset_index(drop=True)
            validation = train.loc[mask].reset_index(drop=True)
            fit = fit_curve(sub, smoothing=lam, config=config)
            scores.append(metrics(validation, PricingEngine(validation).quote(fit.curve))["weighted_huber_loss"])
        if not scores:
            raise ValueError("not enough groups for inner smoothing validation")
        tuning.append({"smoothing": lam, "fold_losses": scores, "mean_loss": float(np.mean(scores))})
    chosen = min(tuning, key=lambda x: (x["mean_loss"], -x["smoothing"]))["smoothing"]
    fits = {"baseline": fit_curve(train, "baseline", config=config, robust=True),
            "advanced": fit_curve(train, smoothing=chosen, config=config)}
    comparison = {"validation_method": "Deterministic dispersed maturity buckets; all instrument types at nearby tenors assigned together; endpoints retained in training.",
                  "training_n": len(train), "holdout_n": len(test),
                  "holdout_instrument_ids": test.instrument_id.tolist(),
                  "holdout_maturity_groups": sorted(set(maturity_groups(test))),
                  "inner_cv": {"folds": 3, "criterion": "mean liquidity-weighted Huber loss in bid/ask uncertainty units", "results": tuning},
                  "chosen_smoothing": chosen,
                  "preprocessing_caveat": "Deterministic quote-unit repair uses contemporaneous peers in the entire visible tape before splitting. The holdout tests curve interpolation; it is not an untouched temporal or ground-truth test.",
                  "evaluation_policy": "All usable validation quotes included; no residual-based deletion or validation reweighting. Report both robust score and uncapped RMSE."}
    for kind, fit in fits.items():
        comparison[kind] = {"train": metrics(train, fit.quotes),
                            "holdout": metrics(test, PricingEngine(test).quote(fit.curve)),
                            "fit_iterations": fit.iterations, "converged": fit.converged}
    held_predictions = {k: PricingEngine(test).quote(v.curve) for k, v in fits.items()}
    comparison["holdout_predictions"] = [
        {"instrument_id": r.instrument_id, "instrument_type": r.instrument_type,
         "maturity_years": float(r.maturity_years), "market_quote": float(r.normalized_quote),
         "sigma": float(r.sigma), "reliability": float(r.reliability),
         "baseline_model_quote": float(held_predictions["baseline"][i]),
         "advanced_model_quote": float(held_predictions["advanced"][i])}
        for i, r in enumerate(test.itertuples())]
    base = comparison["baseline"]["holdout"]["weighted_huber_loss"]
    advanced = comparison["advanced"]["holdout"]["weighted_huber_loss"]
    improvement = 1 - advanced / max(base, 1e-12)
    selected = "advanced" if improvement > 0.05 else "baseline"
    comparison.update(model_selected=selected, relative_holdout_improvement=improvement,
                      selection_rationale=f"Require >5% lower holdout weighted Huber loss for added complexity. Advanced improves by {improvement:.1%}; select {selected}. This is provisional single-snapshot evidence, not a significance claim.")
    full = {"baseline": fit_curve(frame, "baseline", config=config, robust=True),
            "advanced": fit_curve(frame, smoothing=chosen, config=config)}
    for kind, fit in full.items():
        comparison[kind]["full_sample"] = metrics(frame, fit.quotes)
        comparison[kind]["full_fit_iterations"] = fit.iterations
        comparison[kind]["full_fit_condition_number"] = fit.condition_number
        comparison[kind]["robust_residual_scale"] = fit.residual_scale
    ordinary = fit_curve(train, "baseline", config=config)
    ordinary_full = fit_curve(frame, "baseline", config=config)
    comparison["ordinary_least_squares_ablation"] = {
        "train": metrics(train, ordinary.quotes),
        "holdout": metrics(test, PricingEngine(test).quote(ordinary.curve)),
        "full_sample": metrics(frame, ordinary_full.quotes),
        "purpose": "Separate robust estimation benefit from additional spline flexibility. The simple baseline and advanced model share identical spread/liquidity/Huber treatment."}
    return comparison, full, holdout


def sensitivity_studies(frame, fits, comparison, config=Config()):
    grid = np.linspace(1 / 12, 30, config.grid_rows)
    reference = fits["advanced"].curve
    lam = comparison["chosen_smoothing"]

    def outcome(fit):
        dz = (fit.curve.zero(grid) - reference.zero(grid)) * 1e4
        df = (fit.curve.forward(grid) - reference.forward(grid)) * 1e4
        return {"rms_zero_change_bp": float(np.sqrt(np.mean(dz**2))),
                "max_abs_zero_change_bp": float(np.max(abs(dz))),
                "max_abs_forward_change_bp": float(np.max(abs(df))),
                "short_end_max_abs_zero_change_bp": float(np.max(abs(dz[grid <= 1]))),
                "long_end_max_abs_zero_change_bp": float(np.max(abs(dz[grid >= 20]))),
                "zero_30y_bp": float(fit.curve.zero([30])[0] * 1e4),
                "converged": fit.converged, "iterations": fit.iterations}

    result = {"reference": "Advanced full-sample fit; selected model may differ.",
              "smoothing": [], "outlier_threshold": [], "remove_10_percent": [],
              "liquidity_weighting": {}, "terminal_coupon_assumption": [], "edge_behavior": {}}
    sensitivity_curves = []
    for value in sorted(set((lam / 10, lam, lam * 10))):
        fit = fit_curve(frame, smoothing=value, config=config)
        result["smoothing"].append({"smoothing": value, **outcome(fit)})
        sensitivity_curves.append((f"λ={value:g}", fit.curve))
    for value in (1.5, 2.5, 4.0):
        fit = fit_curve(frame, smoothing=lam, threshold=value, config=config)
        result["outlier_threshold"].append({"huber_threshold": value, **outcome(fit),
                                            "weights_below_half": int((fit.robust_weights < 0.5).sum())})
    rng = np.random.default_rng(config.seed)
    for trial in range(config.removal_trials):
        removed = np.sort(rng.choice(len(frame), max(1, round(0.1 * len(frame))), replace=False))
        keep = np.ones(len(frame), dtype=bool)
        keep[removed] = False
        fit = fit_curve(frame.loc[keep].reset_index(drop=True), smoothing=lam, config=config)
        result["remove_10_percent"].append({"trial": trial + 1, "removed_count": len(removed),
                                            "removed_instrument_ids": frame.iloc[removed].instrument_id.tolist(), **outcome(fit)})
    fit = fit_curve(frame, smoothing=lam, liquidity=False, config=config)
    result["liquidity_weighting"] = {"perturbation": "Set all reliability multipliers to one; spread scales unchanged", **outcome(fit)}
    for value in ("none", "full"):
        fit = fit_curve(frame, smoothing=lam, bond_stub=value, config=config)
        result["terminal_coupon_assumption"].append({"alternative": value, **outcome(fit),
                                                    "fit_metrics": metrics(frame, fit.quotes)})
    for kind, fit in fits.items():
        curves = fit.curve
        forward = curves.forward(grid)
        result["edge_behavior"][kind] = {"zero_1month": float(curves.zero([1 / 12])[0]),
                                         "zero_30y": float(curves.zero([30])[0]),
                                         "forward_min": float(np.min(forward)), "forward_max": float(np.max(forward)),
                                         "forward_0": float(curves.forward([0])[0]),
                                         "forward_30y": float(curves.forward([30])[0]),
                                         "forward_40y": float(curves.forward([40])[0]),
                                         "negative_forward_grid_count": int((forward < 0).sum()),
                                         "observed_maturity_min": float(frame.maturity_years.min()),
                                         "observed_maturity_max": float(frame.maturity_years.max())}
    return result, sensitivity_curves
