"""Evidence-based selection, profile support and direction diagnostics for RB-F06."""

from __future__ import annotations

import math

import numpy as np


def _finite_q(record):
    q = record.get("q")
    return q is not None and math.isfinite(float(q))


def best_records(records):
    """Keep best finite and best solver-converged solutions separately."""
    finite = [record for record in records if _finite_q(record)]
    converged = [record for record in finite if record.get("success") is True]
    return {
        "finite": min(finite, key=lambda r: r["q"]) if finite else None,
        "converged": min(converged, key=lambda r: r["q"]) if converged else None,
    }


def dataset_support(baseline_q, profiles, truth_q, threshold=3.841458820694124, tolerance=1e-6):
    """Classify pointwise truth support, invalidating an insufficient dataset baseline."""
    reasons = []
    if baseline_q is None or not math.isfinite(float(baseline_q)):
        reasons.append("no_converged_baseline")
    else:
        audit_points = list(profiles) + [
            item if isinstance(item, dict) else {"q": item, "success": True} for item in truth_q
        ]
        for point in audit_points:
            if _finite_q(point) and point["q"] < baseline_q - tolerance:
                reasons.append("profile_improves_unrestricted_baseline")
            slice_q = point.get("slice_q")
            if (
                slice_q is not None
                and math.isfinite(float(slice_q))
                and slice_q < baseline_q - tolerance
            ):
                reasons.append("slice_improves_unrestricted_baseline")
            if (
                point.get("success") is True
                and _finite_q(point)
                and point.get("slice_q") is not None
                and point["q"] > point["slice_q"] + tolerance
            ):
                reasons.append("profile_worse_than_feasible_slice")
    if reasons:
        return {
            "status": "unsupported",
            "reasons": sorted(set(reasons)),
            "truth_outcomes": ["unknown"] * len(truth_q),
        }
    outcomes = []
    for item in truth_q:
        value = item.get("q") if isinstance(item, dict) else item
        valid = item.get("success") is True if isinstance(item, dict) else True
        if not valid or value is None or not math.isfinite(float(value)):
            outcomes.append("unknown")
        elif value - baseline_q <= threshold:
            outcomes.append("included")
        else:
            outcomes.append("excluded")
    return {
        "status": "supported" if "unknown" not in outcomes else "supported_with_unknown",
        "reasons": [],
        "truth_outcomes": outcomes,
    }


def inclusion_summary(outcomes):
    """Separate unknown from non-inclusion and retain the original outer denominator."""
    if any(value not in {"included", "excluded", "unknown"} for value in outcomes):
        raise ValueError("unrecognized truth outcome")
    n = len(outcomes)
    counts = {name: outcomes.count(name) for name in ("included", "excluded", "unknown")}
    known = counts["included"] + counts["excluded"]
    interval = None
    rate = counts["included"] / known if known else None
    if known:
        z = 1.959963984540054
        den = 1 + z * z / known
        center = (rate + z * z / (2 * known)) / den
        half = z * math.sqrt(rate * (1 - rate) / known + z * z / (4 * known**2)) / den
        interval = [max(0.0, center - half), min(1.0, center + half)]
    return {
        **counts,
        "denominator": n,
        "known_denominator": known,
        "known_rate": rate,
        "known_wilson95": interval,
        "original_rate_bounds": [
            counts["included"] / n,
            (counts["included"] + counts["unknown"]) / n,
        ]
        if n
        else None,
        "interpretation": "descriptive pointwise inclusion, not certified confidence coverage",
    }


def profile_segments(points, baseline_q, threshold, bounds):
    """Preserve all sampled crossings/components without asserting unseen interiors."""
    ordered = sorted(points, key=lambda p: p["value"])
    valid = [p.get("success") is True and _finite_q(p) for p in ordered]
    accepted = [
        ok and p["q"] - baseline_q <= threshold for ok, p in zip(valid, ordered, strict=True)
    ]
    components, crossings, unknown = [], [], []
    active = None
    for i, (point, included) in enumerate(zip(ordered, accepted, strict=True)):
        if included:
            if active is None:
                active = [point["value"], point["value"]]
            active[1] = point["value"]
        elif active is not None:
            components.append(active)
            active = None
        if i and valid[i - 1] and valid[i]:
            if accepted[i - 1] != included:
                crossings.append([ordered[i - 1]["value"], point["value"]])
        elif i:
            unknown.append([ordered[i - 1]["value"], point["value"]])
    if active is not None:
        components.append(active)
    return {
        "observed_components": components,
        "crossing_brackets": crossings,
        "unknown_brackets": unknown,
        "lower_censored": bool(ordered and accepted[0] and ordered[0]["value"] == bounds[0]),
        "upper_censored": bool(ordered and accepted[-1] and ordered[-1]["value"] == bounds[1]),
        "guaranteed_full_support": False,
        "interior_limit": "unexplored gaps can contain additional crossings/support components",
    }


def jacobian_stability(jacobians, rank_rtol=1e-8, matrix_rtol=1e-5, direction_rtol=0.01):
    """Estimate numerical rank/direction stability across steps; no rigorous error bound."""
    js = [np.asarray(j, dtype=float) for j in jacobians]
    if not js or any(j.ndim != 2 or j.shape[1] != 3 or not np.isfinite(j).all() for j in js):
        raise ValueError("finite quote-by-three Jacobians required")
    reference = js[len(js) // 2]
    changes = [float(np.linalg.norm(j - reference, 2)) for j in js]
    error = max(changes)
    norm = max(float(np.linalg.norm(reference, 2)), np.finfo(float).tiny)
    sv, vectors, ranks = [], [], []
    for j in js:
        _, singular, vh = np.linalg.svd(j, full_matrices=True)
        singular = np.pad(singular, (0, 3 - len(singular)))
        sv.append(singular.tolist())
        vectors.append(vh)
        ranks.append(int(np.sum(singular > rank_rtol * max(singular[0], np.finfo(float).tiny))))
    rank = ranks[len(ranks) // 2]
    unresolved = len(set(ranks)) != 1 or error / norm > matrix_rtol
    smallest = sv[len(sv) // 2][rank - 1] if rank else 0.0
    if rank and smallest <= 10 * error:
        unresolved = True
    projectors = [v[rank:].T @ v[rank:] if rank < 3 else np.outer(v[-1], v[-1]) for v in vectors]
    center = projectors[len(projectors) // 2]
    direction_changes = [float(np.linalg.norm(p - center, 2)) for p in projectors]
    if max(direction_changes) > direction_rtol:
        unresolved = True
    return {
        "status": "numerical_unresolved" if unresolved else "stable_estimate",
        "ranks": ranks,
        "singular_values_by_step": sv,
        "estimated_delta_j_norm": error,
        "relative_matrix_change": error / norm,
        "smallest_nonzero_to_estimated_error": smallest / error if error else None,
        "direction_projector_changes": direction_changes,
        "limitation": "step differences estimate numerical uncertainty; not a proof of structural/global identification",
    }


def summarize(record, arrays):
    """Rebuild dataset/cell statistics from original slots and raw saved fit arrays.

    Profile support is pointwise and numerically estimated. Reported holdout
    ranges cover a finite sampled set, not a simultaneous confidence envelope.
    """
    protocol = record["protocol"]
    rows = []
    totals = {
        "attempts": 0,
        "failed": 0,
        "boundary_attempts": 0,
        "residual_calls": 0,
        "diagnostic_calls": 0,
        "scalar_iv_evaluations": 0,
        "fit_seconds": 0.0,
        "evaluation_count_unknown_attempts": 0,
        "fit_seconds_unknown_attempts": 0,
        "stability_iv_calls": 0,
        "stability_scalar_iv_evaluations": 0,
        "stability_seconds": 0.0,
        "cost_scope": "known measured amounts; incomplete if unknown_attempts>0",
    }
    for dataset in record["datasets"]:
        fits = dataset.get("fits", [])
        unrestricted = [fit for fit in fits if fit.get("kind") == "unrestricted"]
        selection = best_records(unrestricted)
        best = selection["converged"]
        baseline = best["q"] if best else None
        points = dataset.get("profile_points", [])
        witnesses = list(points) + [fit for fit in fits if fit.get("kind") == "profile"]
        if selection["finite"]:
            witnesses.append(selection["finite"])
        witnesses += [
            {"q": point["slice_q"], "success": False}
            for point in points
            if point.get("slice_q") is not None
        ]
        point_by_id = {point["point_id"]: point for point in points}
        truth_points = [
            point_by_id.get(pid, {"q": None, "success": False})
            for pid in dataset.get("truth_points", [])
        ]
        if len(truth_points) != 3:
            truth_points = [{"q": None, "success": False}] * 3
        support = dataset_support(
            baseline,
            witnesses,
            truth_points,
            protocol["profile_threshold"],
            protocol["baseline_improvement_tolerance"],
        )
        for fit in fits:
            totals["attempts"] += 1
            totals["failed"] += int(fit.get("success") is not True)
            for key in ("residual_calls", "diagnostic_calls", "scalar_iv_evaluations"):
                totals[key] += int(fit.get(key) or 0)
            totals["evaluation_count_unknown_attempts"] += int(
                any(
                    fit.get(key) is None
                    for key in ("residual_calls", "diagnostic_calls", "scalar_iv_evaluations")
                )
            )
            totals["fit_seconds_unknown_attempts"] += int(fit.get("seconds") is None)
            totals["fit_seconds"] += float(fit.get("seconds") or 0.0)
            totals["stability_iv_calls"] += int(fit.get("stability_iv_calls") or 0)
            totals["stability_scalar_iv_evaluations"] += int(
                fit.get("stability_scalar_iv_evaluations") or 0
            )
            totals["stability_seconds"] += float(fit.get("stability_seconds") or 0.0)
            flags = fit.get("array_keys", {}).get("boundary_flags")
            totals["boundary_attempts"] += int(flags is not None and np.any(arrays[flags]))
        row = {
            "dataset_id": dataset["dataset_id"],
            "truth_index": dataset["truth_index"],
            "group": dataset["group"],
            "rep": dataset["rep"],
            "support": support,
            "best_converged": best["fit_id"] if best else None,
            "best_finite": selection["finite"]["fit_id"] if selection["finite"] else None,
            "best_q": baseline,
            "max_iv_residual": None,
            "scaled_parameter_distance": None,
            "theta": None,
            "numerical_stability": None,
            "holdout": None,
            "sampled_price_range": None,
        }
        if best:
            keys = best["array_keys"]
            theta = np.asarray(arrays[keys["theta"]])
            residual = np.asarray(arrays[keys["raw_residual"]])
            truth = np.asarray(protocol["truths"][dataset["truth_index"]]["theta"])
            row["theta"] = theta.tolist()
            row["max_iv_residual"] = float(np.max(np.abs(residual)))
            row["scaled_parameter_distance"] = float(
                np.linalg.norm((theta - truth) / protocol["parameter_scale"])
            )
            row["numerical_stability"] = best.get("numerical_stability")
            if "holdout_iv" in keys:
                predicted_iv = arrays[keys["holdout_iv"]]
                predicted_price = arrays[keys["holdout_prices"]]
                target_iv = arrays[dataset["holdout_truth_iv_key"]]
                target_price = arrays[dataset["holdout_truth_prices_key"]]
                row["holdout"] = {
                    "iv_max_error": float(np.max(np.abs(predicted_iv - target_iv))),
                    "iv_rmse": float(np.sqrt(np.mean((predicted_iv - target_iv) ** 2))),
                    "price_max_error": float(np.max(np.abs(predicted_price - target_price))),
                    "price_rmse": float(np.sqrt(np.mean((predicted_price - target_price) ** 2))),
                    "price_over_forward_max_error": float(
                        np.max(np.abs(predicted_price - target_price)) / protocol["forward"]
                    ),
                }
                selected = []
                threshold = (
                    protocol["noiseless_delta_q"]
                    if dataset["rep"] == -1
                    else protocol["profile_threshold"]
                )
                for fit in fits:
                    fkeys = fit.get("array_keys", {})
                    if (
                        fit.get("success") is not True
                        or not _finite_q(fit)
                        or "holdout_prices" not in fkeys
                    ):
                        continue
                    if fit["q"] - baseline > threshold:
                        continue
                    if (
                        dataset["rep"] == -1
                        and np.max(np.abs(arrays[fkeys["raw_residual"]]))
                        > protocol["noiseless_max_iv_error"]
                    ):
                        continue
                    selected.append(arrays[fkeys["holdout_prices"]])
                if selected:
                    prices = np.vstack(selected)
                    row["sampled_price_range"] = {
                        "count": len(selected),
                        "minimum": np.min(prices, axis=0).tolist(),
                        "maximum": np.max(prices, axis=0).tolist(),
                        "width": np.ptp(prices, axis=0).tolist(),
                        "support_status": support["status"],
                        "interpretation": "finite converged visits under pointwise reference threshold, not joint-confidence envelope",
                    }
        rows.append(row)
    cells = []
    identities = sorted({(row["truth_index"], row["group"]) for row in rows})
    for truth_index, group in identities:
        selected = [r for r in rows if (r["truth_index"], r["group"]) == (truth_index, group)]
        noisy = [r for r in selected if r["rep"] >= 0]
        solved = [r for r in noisy if r["theta"] is not None]
        theta = np.array([r["theta"] for r in solved])
        cells.append(
            {
                "truth_index": truth_index,
                "truth_name": protocol["truths"][truth_index]["name"],
                "group": group,
                "original_noisy_slots": len(noisy),
                "converged_noisy_slots": len(solved),
                "unsupported_noisy_slots": sum(
                    r["support"]["status"] == "unsupported" for r in noisy
                ),
                "pointwise_inclusion": [
                    inclusion_summary([r["support"]["truth_outcomes"][axis] for r in noisy])
                    for axis in range(3)
                ],
                "parameter_minimum": np.min(theta, axis=0).tolist() if solved else None,
                "parameter_maximum": np.max(theta, axis=0).tolist() if solved else None,
                "max_scaled_parameter_error": max(
                    (r["scaled_parameter_distance"] for r in solved), default=None
                ),
                "max_holdout_iv_error": max(
                    (r["holdout"]["iv_max_error"] for r in solved if r["holdout"]), default=None
                ),
                "max_holdout_price_error": max(
                    (r["holdout"]["price_max_error"] for r in solved if r["holdout"]), default=None
                ),
                "jacobian_unresolved_slots": sum(
                    r["numerical_stability"] is not None
                    and r["numerical_stability"]["status"] == "numerical_unresolved"
                    for r in solved
                ),
            }
        )
    return {
        "schema": "RB-F06-summary-v1",
        "phase": record.get("phase"),
        "per_dataset": rows,
        "cells": cells,
        "cost_totals": totals,
        "claims": {
            "exact_sabr_validated": False,
            "global_identification_proven": False,
            "guaranteed_confidence_coverage": False,
            "joint_price_envelope": False,
        },
    }
