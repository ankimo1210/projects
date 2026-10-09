"""Private, Torch-free quote risk and paired scores for dynamic hedging.

Unknown numerical results remain NaN. The only holding projection is the
declared legal portfolio constraint of [-2, 2] contracts per asset; raw
targets and band holdings are retained. No calibration or bootstrap is run.
"""

from __future__ import annotations

import numpy as np


def _broadcast(*values):
    return np.broadcast_arrays(*(np.asarray(value, dtype=float) for value in values))


def _model_parameters(model, spot, xi, rho):
    if model not in {"heston", "local"}:
        raise ValueError("model must be heston or local")
    if np.any(spot <= 0) or np.any(xi < 0) or np.any(np.abs(rho) > 1):
        raise ValueError("spot must be positive, xi nonnegative and |rho| <= 1")


def quote_positions(v_s, v_theta, c_s, c_theta, *, denominator_error=0.0) -> dict:
    """Return stock/call IFT targets in observable (S, Q) coordinates.

    Inputs broadcast to a common shape, retained by every output array.
    Derivatives hold time and Asian memory fixed. ``denominator_error`` is
    an independently assessed absolute error in C_theta, in the same state
    coordinate. |C_theta| <= 3 error and nonfinite ratios are unknown; the
    denominator and its error remain available for downstream qualification.
    State-scale, support and root-uniqueness gates belong to the fit caller.
    """
    vs, vt, cs, ct, error = _broadcast(v_s, v_theta, c_s, c_theta, denominator_error)
    if np.any(error < 0):
        raise ValueError("denominator_error must be nonnegative")
    valid = np.logical_and.reduce([np.isfinite(x) for x in (vs, vt, cs, ct, error)])
    valid &= np.abs(ct) > 3 * error
    call = np.full(ct.shape, np.nan)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        np.divide(vt, ct, out=call, where=valid)
        stock = vs - call * cs
    valid &= np.isfinite(stock) & np.isfinite(call)
    return {
        "stock": np.where(valid, stock, np.nan),
        "call": np.where(valid, call, np.nan),
        "denominator": ct.copy(),
        "denominator_error": error.copy(),
        "valid": valid,
        "status": np.where(valid, "ok", "unknown"),
    }


def stock_only_target(positions: dict, c_s, c_theta, *, model, spot, xi=0.0, rho=0.0):
    """Project quote exposure into the minimum-variance stock hedge.

    For Heston C_theta is the physical C_v derivative, even if the supplied
    quote positions were computed in log-state coordinates. Local forecasts
    freeze their multiplier, so beta = C_s. Return a broadcast array of raw
    targets; unknown inputs remain NaN and no holding constraints are applied.
    """
    hs, hq, cs, ct, s, volvol, corr = _broadcast(
        positions["stock"], positions["call"], c_s, c_theta, spot, xi, rho
    )
    _model_parameters(model, s, volvol, corr)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        beta = cs + ct * corr * volvol / s if model == "heston" else cs
        target = hs + hq * beta
    valid = np.logical_and.reduce([np.isfinite(x) for x in (hs, hq, cs, ct, s, volvol, corr)])
    valid &= np.asarray(positions["valid"], dtype=bool) & np.isfinite(target)
    return np.where(valid, target, np.nan)


def price_covariance(model, spot, state, c_s, c_theta, dt, *, xi=0.0, rho=0.0, base_variance=None):
    """Return the local stock/call diffusion covariance in currency squared.

    Heston state is physical current variance and C_theta is C_v. Local state
    is the frozen forecast variance multiplier; base_variance is the local
    base field at this calendar/spot state. The interval dt is in years.
    Output covariance has broadcast input shape + (2, 2); rank/valid/status
    retain that input shape. The local matrix has rank <= 1 with no ridge.
    This is a continuous diffusion approximation, not finite-step covariance.
    """
    if model == "local" and base_variance is None:
        raise ValueError("local covariance requires base_variance")
    s, theta, cs, ct, interval, volvol, corr, base = _broadcast(
        spot, state, c_s, c_theta, dt, xi, rho, 1.0 if base_variance is None else base_variance
    )
    _model_parameters(model, s, volvol, corr)
    if np.any(theta < 0) or np.any(base < 0) or np.any(interval < 0):
        raise ValueError("variance, multiplier, base_variance and dt must be nonnegative")
    if model == "local" and np.any(theta == 0):
        raise ValueError("local forecast multiplier must be positive")
    valid = np.logical_and.reduce(
        [np.isfinite(x) for x in (s, theta, cs, ct, interval, volvol, corr, base)]
    )
    with np.errstate(over="ignore", invalid="ignore"):
        variance = theta if model == "heston" else theta * base
        first = s * cs + corr * volvol * ct if model == "heston" else s * cs
        second = volvol * np.sqrt(1 - corr**2) * ct if model == "heston" else np.zeros(s.shape)
        covariance = np.empty((*s.shape, 2, 2))
        covariance[..., 0, 0] = variance * interval * s**2
        covariance[..., 0, 1] = covariance[..., 1, 0] = variance * interval * s * first
        covariance[..., 1, 1] = variance * interval * (first**2 + second**2)
    valid &= np.isfinite(covariance).all(axis=(-2, -1))
    covariance = np.where(valid[..., None, None], covariance, np.nan)
    rank = np.full(s.shape, -1, dtype=int)
    rank[valid] = np.linalg.matrix_rank(covariance[valid])
    return {
        "covariance": covariance,
        "rank": rank,
        "valid": valid,
        "status": np.where(valid, "ok", "unknown"),
    }


def band_holdings(old, target, covariance, width: float) -> dict:
    """Apply the covariance SD band, then the legal [-2, 2] action constraint.

    Holdings have shape (..., assets), assets is one or two. Covariance has
    shape (..., assets, assets) and broadcasts over portfolio rows. The band
    holds old at sd <= width, including a rank-deficient null direction.
    Raw target, raw band holdings, per-component constraints, row counts and
    total count are saved. Nonfinite rows remain unknown, never implicit hold.
    A finite asymmetric or materially indefinite covariance is a caller error;
    tiny negative eigenvalues are tolerated as arithmetic error without repair.
    """
    if not np.isfinite(width) or width < 0:
        raise ValueError("width must be finite and nonnegative")
    old, target = _broadcast(old, target)
    if old.ndim < 1 or old.shape[-1] not in {1, 2}:
        raise ValueError("holdings must have a final axis of one or two assets")
    assets = old.shape[-1]
    cov = np.asarray(covariance, dtype=float)
    if cov.shape[-2:] != (assets, assets):
        raise ValueError("covariance asset axes must match holdings")
    shape = np.broadcast_shapes(old.shape[:-1], cov.shape[:-2])
    old = np.broadcast_to(old, (*shape, assets))
    target = np.broadcast_to(target, old.shape)
    cov = np.broadcast_to(cov, (*shape, assets, assets))
    finite_cov = np.isfinite(cov).all(axis=(-2, -1))
    finite_matrices = cov[finite_cov]
    tolerance = 16 * np.finfo(float).eps * np.max(np.abs(finite_matrices), axis=(-2, -1))
    asymmetric = np.max(np.abs(finite_matrices - finite_matrices.swapaxes(-1, -2)), axis=(-2, -1))
    eigenvalues = np.linalg.eigvalsh(finite_matrices)
    if np.any(asymmetric > tolerance) or np.any(eigenvalues[..., 0] < -tolerance):
        raise ValueError("covariance must be symmetric positive semidefinite")
    valid = finite_cov & np.isfinite(old).all(axis=-1) & np.isfinite(target).all(axis=-1)
    with np.errstate(over="ignore", invalid="ignore"):
        delta = old - target
        squared_sd = np.einsum("...i,...ij,...j->...", delta, cov, delta)
    raw_squared_sd = squared_sd.copy()
    # PSD quadratic forms can cancel to a tiny negative value in null directions.
    # Retain the raw result and explicitly record this arithmetic correction;
    # this bound does not qualify materially negative or nonfinite forms.
    with np.errstate(over="ignore", invalid="ignore"):
        roundoff_bound = (
            16
            * np.finfo(float).eps
            * np.einsum("...i,...ij,...j->...", np.abs(delta), np.abs(cov), np.abs(delta))
        )
    roundoff_corrected = (
        valid
        & np.isfinite(squared_sd)
        & np.isfinite(roundoff_bound)
        & (squared_sd < 0)
        & (squared_sd >= -roundoff_bound)
    )
    squared_sd = np.where(roundoff_corrected, 0.0, squared_sd)
    valid &= np.isfinite(squared_sd) & (squared_sd >= 0)
    sd = np.full(shape, np.nan)
    np.sqrt(squared_sd, out=sd, where=valid)
    raw = np.full(old.shape, np.nan)
    hold = valid & (sd <= width)
    trade = valid & (sd > width)
    raw[hold] = old[hold]
    with np.errstate(over="ignore", invalid="ignore"):
        raw[trade] = target[trade] + (width / sd[trade])[..., None] * delta[trade]
    valid &= np.isfinite(raw).all(axis=-1)
    raw = np.where(valid[..., None], raw, np.nan)
    holdings = np.clip(raw, -2.0, 2.0)
    constrained = valid[..., None] & (holdings != raw)
    counts = constrained.sum(axis=-1)
    return {
        "raw_target": target.copy(),
        "raw_holdings": raw,
        "holdings": holdings,
        "sd": sd,
        "raw_squared_sd": raw_squared_sd,
        "squared_sd_roundoff_bound": roundoff_bound,
        "roundoff_corrected": roundoff_corrected,
        "roundoff_correction_count": int(roundoff_corrected.sum()),
        "constrained": constrained,
        "constraint_counts": counts,
        "constraint_count": int(counts.sum()),
        "valid": valid,
        "status": np.where(valid, "ok", "unknown"),
    }


def improvement_scores(base_squared, candidate_squared, relative_improvement: float = 0.05) -> dict:
    """Retain paired absolute/relative scores on every original path.

    d = candidate_squared - base_squared; r = candidate_squared -
    (1-relative_improvement)*base_squared. Both contain the random original
    baseline. Inputs must have identical nonempty shape; no pair is filtered.
    Means and IID sample SEs use original_count. Any nonfinite original pair
    makes all aggregate statistics unknown. Singleton SEs are unknown too.
    These are raw scores and descriptive IID summaries, not a support decision
    or a bootstrap confidence interval. Scores are in currency squared.
    """
    base, candidate = (
        np.asarray(base_squared, dtype=float),
        np.asarray(candidate_squared, dtype=float),
    )
    if base.shape != candidate.shape or base.size == 0:
        raise ValueError("nonempty original paired arrays must have identical shapes")
    if not np.isfinite(relative_improvement) or not 0 <= relative_improvement <= 1:
        raise ValueError("relative_improvement must be between zero and one")
    if np.any(base < 0) or np.any(candidate < 0):
        raise ValueError("squared losses must be nonnegative")
    with np.errstate(over="ignore", invalid="ignore"):
        d = candidate - base
        r = candidate - (1 - relative_improvement) * base
    valid = np.isfinite(base) & np.isfinite(candidate) & np.isfinite(d) & np.isfinite(r)
    count = base.size
    complete = bool(valid.all())
    result = {
        "d": d,
        "r": r,
        "absolute": d,
        "relative": r,
        "original_count": count,
        "valid_count": int(valid.sum()),
        "invalid_count": int(count - valid.sum()),
        "valid": valid,
        "status": "ok" if complete and count > 1 else "unknown",
    }
    for name, score in (("d", d), ("r", r)):
        result[f"{name}_mean"] = float(np.mean(score)) if complete else np.nan
        result[f"{name}_se"] = (
            float(np.std(score, ddof=1) / np.sqrt(count)) if complete and count > 1 else np.nan
        )
    return result
