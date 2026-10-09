"""Private Torch-free statistics for the frozen dynamic-hedging protocol.

Loss L is minus discounted net P&L, supplied by the caller in currency.
Squared-loss scores and envelopes are in currency squared. These functions
do not certify numerical accuracy, training completion, or Q diagnostics.
Only index creation draws randomness; saved replay consumes supplied indices.
"""

from __future__ import annotations

import numpy as np


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _loss_array(losses):
    values = np.asarray(losses, dtype=float)
    if values.ndim != 2 or values.shape[0] != 3 or values.shape[1] == 0:
        raise ValueError("losses must have nonempty shape (3, N)")
    return values


def _counts(valid):
    original = np.full(3, valid.shape[1], dtype=int)
    finite = valid.sum(axis=1)
    return {
        "original_per_seed": original,
        "finite_per_seed": finite,
        "unknown_per_seed": original - finite,
        "original": int(valid.size),
        "finite": int(finite.sum()),
        "unknown": int(valid.size - finite.sum()),
    }


def _iid_moments(values):
    n = values.shape[1]
    complete = bool(np.isfinite(values).all())
    per_seed_mean = np.full(3, np.nan)
    per_seed_variance = np.full(3, np.nan)
    mean, variance, se, pooled_se = (np.nan,) * 4
    if complete:
        with np.errstate(over="ignore", invalid="ignore"):
            per_seed_mean = np.mean(values, axis=1)
            mean = float(np.mean(per_seed_mean))
            variance = float(np.var(values, ddof=1))
            pooled_se = float(np.sqrt(variance / values.size))
            if n > 1:
                per_seed_variance = np.var(values, axis=1, ddof=1)
                se = float(np.sqrt(np.sum(per_seed_variance / n)) / 3)
    return {
        "mean": mean,
        "variance": variance,
        "se": se,
        "pooled_se": pooled_se,
        "per_seed_mean": per_seed_mean,
        "per_seed_variance": per_seed_variance,
    }


def _finite_description(losses, valid):
    values = losses[valid]
    count = values.size
    tail_count = max(1, (count + 19) // 20) if count else 0
    with np.errstate(over="ignore", invalid="ignore"):
        result = {
            "status": "descriptive_only",
            "count": int(count),
            "mean_loss": float(np.mean(values)) if count else np.nan,
            "mse": float(np.mean(values**2)) if count else np.nan,
            "variance": float(np.var(values, ddof=1)) if count > 1 else np.nan,
            "es95": float(np.mean(np.sort(values)[-tail_count:])) if count else np.nan,
            "es95_tail_count": tail_count,
        }
    metrics = ("mean_loss", "mse", "variance", "es95")
    complete = all(np.isfinite(result[name]) for name in metrics)
    for name in metrics:
        if not np.isfinite(result[name]):
            result[name] = np.nan
    result["arithmetic_status"] = "ok" if complete else "unknown"
    return result


def make_bootstrap_indices(blocks_per_seed, *, seed, replicates=2000) -> np.ndarray:
    """Draw local seed-stratified block selections as int16 (R, 3, B).

    B is the number of equal blocks in each original test seed. Each of the
    three seed strata draws B blocks with replacement independently in each
    replicate. The caller creates this array once and shares it across every
    method, generator and initialization. SeedSequence/Generator are local;
    NumPy's global RNG state is unchanged. B <= 32768 keeps indices in int16.
    """
    blocks = _positive_integer(blocks_per_seed, "blocks_per_seed")
    runs = _positive_integer(replicates, "replicates")
    if blocks > np.iinfo(np.int16).max + 1:
        raise ValueError("blocks_per_seed exceeds the int16 index range")
    generator = np.random.default_rng(np.random.SeedSequence(seed))
    return generator.integers(0, blocks, size=(runs, 3, blocks), dtype=np.int16)


def risk_summary(losses, *, block_size=64) -> dict:
    """Summarize all original individual losses of shape (3, N).

    Mean/MSE are equal-weight means over the three seed means. Loss variance
    is the pooled individual sample variance with ddof=1, in currency squared.
    For Y=L or L^2, per-path IID SE uses within-seed sample variances s_j^2
    (ddof=1): sqrt(sum_j(s_j^2/N))/3. Pooled sample SEs are also reported under
    explicit pooled names. These estimate sampling uncertainty, not bias.

    ES95 is the mean of the largest ceil(0.05 * 3N) individual losses, with
    exactly that count even at tied boundaries. Its CI is not evaluated. Block
    means of L and L^2 are retained only when N is divisible by block_size;
    block means are never used as individual tail losses. Any nonfinite path
    makes primary aggregate metrics unknown; finite-only metrics are separately
    descriptive. No path is silently dropped from the original denominator.
    """
    values = _loss_array(losses)
    block_size = _positive_integer(block_size, "block_size")
    with np.errstate(over="ignore", invalid="ignore"):
        squared = values**2
    valid = np.isfinite(values) & np.isfinite(squared)
    complete = bool(valid.all())
    counts = _counts(valid)
    loss_moments = _iid_moments(values if complete else np.full(values.shape, np.nan))
    mse_moments = _iid_moments(squared if complete else np.full(values.shape, np.nan))
    tail_count = (values.size + 19) // 20
    es95 = float(np.mean(np.sort(values.ravel())[-tail_count:])) if complete else np.nan
    divisible = values.shape[1] % block_size == 0
    blocks = None
    if divisible:
        shape = (3, values.shape[1] // block_size, block_size)
        with np.errstate(over="ignore", invalid="ignore"):
            blocks = {
                "loss": np.mean(values.reshape(shape), axis=2),
                "squared_loss": np.mean(squared.reshape(shape), axis=2),
            }
    finite_summary = all(
        np.isfinite(item)
        for item in (
            loss_moments["mean"],
            mse_moments["mean"],
            loss_moments["variance"],
            loss_moments["se"],
            mse_moments["se"],
            es95,
        )
    )
    return {
        "status": "ok" if complete and finite_summary else "unknown",
        "original_count": int(values.size),
        "counts": counts,
        "losses": values.copy(),
        "squared_losses": squared,
        "valid": valid,
        "mean_loss": loss_moments["mean"],
        "mse": mse_moments["mean"],
        "rmse": float(np.sqrt(mse_moments["mean"])),
        "variance": loss_moments["variance"],
        "mean_loss_se": loss_moments["se"],
        "mse_se": mse_moments["se"],
        "pooled_mean_loss_se": loss_moments["pooled_se"],
        "pooled_mse_se": mse_moments["pooled_se"],
        "per_seed": {"loss": loss_moments, "squared_loss": mse_moments},
        "es95": es95,
        "es95_tail_count": tail_count,
        "es95_original_count": int(values.size),
        "es95_ci_status": "not_evaluated",
        "es95_convention": "largest_ceil_0.05_original_individual_count",
        "block_size": block_size,
        "blocks_per_seed": values.shape[1] // block_size if divisible else None,
        "block_status": "ok" if divisible else "not_divisible",
        "block_means": blocks,
        "finite_only": _finite_description(values, valid),
    }


def _bootstrap_from_blocks(blocks, indices):
    # The seed axis is never resampled or pooled before each stratum's mean.
    selected = blocks[np.arange(3)[None, :, None], indices]
    with np.errstate(over="ignore", invalid="ignore"):
        return np.mean(np.mean(selected, axis=2), axis=1)


def _numerical_envelope(envelope):
    result = {}
    for name in ("absolute", "relative"):
        value = None if envelope is None else envelope.get(name)
        if value is None:
            result[name] = None
            continue
        if np.asarray(value).ndim != 0:
            raise ValueError("numerical envelope values must be nonnegative scalars")
        value = float(value)
        if np.isfinite(value) and value < 0:
            raise ValueError("numerical envelope values must be nonnegative scalars")
        result[name] = value
    known = all(value is not None and np.isfinite(value) for value in result.values())
    return result, known


def paired_statistics(
    baseline_loss,
    candidate_loss,
    indices,
    *,
    block_size=64,
    alpha=0.05 / 8,
    numerical_envelope=None,
) -> dict:
    """Recompute paired scores and one-sided upper percentile bounds.

    Inputs are losses L=-discounted net P&L of identical shape (3, N), paired
    by original seed/path IDs. d=L_candidate^2-L_baseline^2 and
    r=L_candidate^2-0.95 L_baseline^2 retain baseline sampling uncertainty.
    Means and IID SEs use the equal-seed formula documented in risk_summary.
    N must be divisible by block_size; supplied integer indices have shape
    (R, 3, N/block_size), contain in-stratum block IDs, and are saved unchanged.
    No RNG is created or consumed. Raw scores, blocks, bootstrap replicates,
    and baseline/candidate mean-loss bootstrap replicates remain replayable.

    U_d/U_r are nominal one-sided 1-alpha percentile bounds using NumPy's
    linear quantile convention, an approximate block-bootstrap procedure.
    Default alpha=.05/8 is the family Bonferroni allocation. No further alpha
    division is made for the two scores or three training initializations.

    Numerical envelopes are nonnegative absolute/relative scalars in currency
    squared. Missing/None/nonfinite values mean unknown; zero denotes a zero
    already measured or justified by the caller. This function invents no
    accuracy evidence. Support requires U_d+u_d < -.001 AND U_r+u_r < 0,
    with strict inequalities. A nonfinite original pair or score makes the
    primary decision unknown; finite-only means are descriptive and never
    determine support. Training and Q-accuracy gates belong to the caller.
    """
    baseline, candidate = _loss_array(baseline_loss), _loss_array(candidate_loss)
    if baseline.shape != candidate.shape:
        raise ValueError("baseline and candidate losses must have identical shapes")
    block_size = _positive_integer(block_size, "block_size")
    if baseline.shape[1] % block_size:
        raise ValueError("each seed's N must be divisible by block_size")
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between zero and one")
    blocks = baseline.shape[1] // block_size
    indices = np.asarray(indices)
    if indices.ndim != 3 or indices.shape[0] == 0 or indices.shape[1:] != (3, blocks):
        raise ValueError("indices must have nonempty shape (R, 3, blocks_per_seed)")
    if (
        not np.issubdtype(indices.dtype, np.integer)
        or np.any(indices < 0)
        or np.any(indices >= blocks)
    ):
        raise ValueError("indices must contain integer block IDs within each seed")
    envelope, envelope_known = _numerical_envelope(numerical_envelope)
    with np.errstate(over="ignore", invalid="ignore"):
        base_squared, candidate_squared = baseline**2, candidate**2
        scores = {
            "absolute": candidate_squared - base_squared,
            "relative": candidate_squared - 0.95 * base_squared,
        }
    valid = np.logical_and.reduce(
        [
            np.isfinite(value)
            for value in (baseline, candidate, base_squared, candidate_squared, *scores.values())
        ]
    )
    complete = bool(valid.all())
    counts = _counts(valid)
    shape = (3, blocks, block_size)
    with np.errstate(over="ignore", invalid="ignore"):
        block_scores = {
            name: np.mean(value.reshape(shape), axis=2) for name, value in scores.items()
        }
    bootstrap = {
        name: _bootstrap_from_blocks(value, indices) for name, value in block_scores.items()
    }
    moments = {
        name: _iid_moments(value if complete else np.full(value.shape, np.nan))
        for name, value in scores.items()
    }
    upper = {
        name: float(np.quantile(value, 1 - alpha, method="linear"))
        if complete and np.isfinite(value).all()
        else np.nan
        for name, value in bootstrap.items()
    }
    finite_moments = all(
        np.isfinite(moment[name])
        for moment in moments.values()
        for name in ("mean", "variance", "se", "pooled_se")
    )
    known = (
        complete
        and envelope_known
        and finite_moments
        and all(np.isfinite(value) for value in upper.values())
    )
    adjusted_upper = {name: upper[name] + envelope[name] if known else np.nan for name in upper}
    known = known and all(np.isfinite(value) for value in adjusted_upper.values())
    conditions = {
        "absolute": bool(adjusted_upper["absolute"] < -0.001) if known else None,
        "relative": bool(adjusted_upper["relative"] < 0) if known else None,
    }
    supported = all(conditions.values()) if known else None
    status = "supported" if supported else "not_supported" if known else "unknown"
    with np.errstate(over="ignore", invalid="ignore"):
        descriptions = {
            name: float(np.mean(value[valid])) if counts["finite"] else np.nan
            for name, value in scores.items()
        }
    descriptive_finite = all(np.isfinite(value) for value in descriptions.values())
    descriptions = {
        name: value if np.isfinite(value) else np.nan for name, value in descriptions.items()
    }
    base_summary = risk_summary(baseline, block_size=block_size)
    candidate_summary = risk_summary(candidate, block_size=block_size)
    return {
        "status": status,
        "risk_improvement_supported": supported,
        "original_count": int(baseline.size),
        "counts": counts,
        "valid": valid,
        "scores": scores,
        "means": {name: value["mean"] for name, value in moments.items()},
        "iid_se": {name: value["se"] for name, value in moments.items()},
        "pooled_iid_se": {name: value["pooled_se"] for name, value in moments.items()},
        "per_seed": moments,
        "block_size": block_size,
        "blocks_per_seed": blocks,
        "block_scores": block_scores,
        "bootstrap_indices": indices.copy(),
        "bootstrap_scores": bootstrap,
        "bootstrap_mean_loss": {
            "baseline": _bootstrap_from_blocks(base_summary["block_means"]["loss"], indices),
            "candidate": _bootstrap_from_blocks(candidate_summary["block_means"]["loss"], indices),
        },
        "baseline_summary": base_summary,
        "candidate_summary": candidate_summary,
        "alpha": float(alpha),
        "confidence": float(1 - alpha),
        "quantile_method": "linear",
        "interval_kind": "nominal_one_sided_upper_percentile_block_bootstrap",
        "upper_bounds": upper,
        "numerical_envelope": envelope,
        "envelope_status": "ok" if envelope_known else "unknown",
        "adjusted_upper_bounds": adjusted_upper,
        "conditions": conditions,
        "finite_only": {
            "status": "descriptive_only",
            "arithmetic_status": "ok" if descriptive_finite else "unknown",
            "count": counts["finite"],
            "means": descriptions,
        },
    }


def family_assessment(initialization_results) -> dict:
    """Apply an intersection-union decision to exactly init 11, 29 and 47.

    Keys may be these integer IDs or their decimal strings. Each result uses
    paired_statistics status and absolute/relative conditions. All three
    initializations must be supported and satisfy both conditions. Any
    failed/unknown/missing condition makes the family unknown, taking priority
    over an unsupported initialization. Otherwise any finite unsupported
    initialization or false condition makes it not_supported. Best-init or
    average-init decisions are not made and alpha is never divided again.
    The caller must mark incomplete training/refinement/Q checks as unknown.
    """
    results = {str(key): value for key, value in initialization_results.items()}
    if len(results) != len(initialization_results) or set(results) != {"11", "29", "47"}:
        raise ValueError("family must contain exactly initialization IDs 11, 29, 47")
    statuses = {key: value.get("status", "unknown") for key, value in results.items()}
    conditions = {key: value.get("conditions", {}) for key, value in results.items()}
    unknown = any(status not in {"supported", "not_supported"} for status in statuses.values())
    unknown |= any(
        not isinstance(conditions[key].get(name), (bool, np.bool_))
        for key in results
        for name in ("absolute", "relative")
    )
    supported = (
        None
        if unknown
        else all(
            statuses[key] == "supported"
            and all(conditions[key][name] for name in ("absolute", "relative"))
            for key in results
        )
    )
    return {
        "status": "unknown" if unknown else "supported" if supported else "not_supported",
        "risk_improvement_supported": supported,
        "initialization_statuses": statuses,
        "initialization_conditions": conditions,
        "initialization_ids": (11, 29, 47),
        "decision_rule": "all_three_initializations_and_both_scores",
    }
