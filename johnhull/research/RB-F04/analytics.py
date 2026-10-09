"""Paired sampling statistics for RB-F04; failed paths are never dropped."""

from __future__ import annotations

import numpy as np


def _monthly(observations):
    values = np.asarray(observations, dtype=float)
    if values.ndim != 2 or values.shape[1] != 13 or values.shape[0] == 0:
        raise ValueError("observations must have shape (paths, 13), including the initial spot")
    return values


def asian_payoffs(observations, strike, rate, expiry):
    """Discount a twelve-observation arithmetic Asian payoff, excluding initial spot."""
    if strike <= 0 or expiry <= 0:
        raise ValueError("strike and expiry must be positive")
    values = _monthly(observations)
    return np.exp(-rate * expiry) * np.maximum(values[:, 1:].mean(axis=1) - strike, 0)


def vanilla_payoffs(observations, times, strikes, rate, expiry):
    """Return discounted payoffs with axes paths, exact monthly times, strikes."""
    values = _monthly(observations)
    times = np.atleast_1d(np.asarray(times, dtype=float))
    strikes = np.atleast_1d(np.asarray(strikes, dtype=float))
    if expiry <= 0 or np.any(strikes <= 0) or np.any(times <= 0) or np.any(times > expiry):
        raise ValueError("expiry/strikes must be positive and times within the contract")
    indices = np.rint(times * 12 / expiry).astype(int)
    if not np.allclose(indices * expiry / 12, times, rtol=0, atol=1e-12):
        raise ValueError("requested times must be exact monthly observation times")
    return np.exp(-rate * times)[None, :, None] * np.maximum(
        values[:, indices, None] - strikes[None, None, :], 0
    )


def sample_summary(samples):
    """Mean and ddof=1 sampling SE along path axis; any missing value invalidates its claim."""
    values = np.asarray(samples, dtype=float)
    if values.ndim == 0 or len(values) == 0:
        raise ValueError("at least one sample is required")
    count = len(values)
    supported = np.all(np.isfinite(values), axis=0) & (count >= 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.mean(values, axis=0)
        se = np.std(values, axis=0, ddof=1) / np.sqrt(count) if count >= 2 else mean * np.nan
    return {
        "samples": count,
        "supported": supported,
        "mean": np.where(supported, mean, np.nan),
        "standard_error": np.where(supported, se, np.nan),
    }


def paired_summary(heston, local):
    """Retain each model estimate and compute the covariance-aware local-minus-Heston SE."""
    heston = np.asarray(heston, dtype=float)
    local = np.asarray(local, dtype=float)
    if heston.shape != local.shape:
        raise ValueError("paired arrays must have identical shape")
    return {
        "heston": sample_summary(heston),
        "local": sample_summary(local),
        "difference": sample_summary(local - heston),
    }


def two_date_summary(heston, local, bins, conditional_threshold=110, minimum_count=32):
    """Joint and conditional bin comparisons, including tails and paired ratio sampling SE.

    Conditional events use each model's own first-date denominator. Their SE uses the
    difference of ratio influence functions, preserving within-path covariance.
    Low-count bins and any failed pair remain explicitly unsupported.
    """
    heston = np.asarray(heston, dtype=float)
    local = np.asarray(local, dtype=float)
    cuts = np.asarray(bins, dtype=float)
    if (
        heston.ndim != 2
        or heston.shape[1] != 2
        or heston.shape != local.shape
        or len(heston) < 2
        or cuts.ndim != 1
        or not np.all(np.isfinite(cuts))
        or np.any(np.diff(cuts) <= 0)
        or minimum_count < 1
    ):
        raise ValueError("paired two-date paths, increasing finite bins and count >=1 required")
    if not np.isfinite(conditional_threshold):
        raise ValueError("conditional threshold must be finite")
    count = len(heston)
    size = len(cuts) + 1
    edges = np.concatenate(([-np.inf], cuts, [np.inf]))
    failures = ~(
        np.all(np.isfinite(heston) & (heston > 0), axis=1)
        & np.all(np.isfinite(local) & (local > 0), axis=1)
    )
    result = {
        "samples": count,
        "failed_pairs": int(failures.sum()),
        "supported": not failures.any(),
        "edges": edges,
        "joint_counts_heston": np.zeros((size, size), dtype=int),
        "joint_counts_local": np.zeros((size, size), dtype=int),
        "joint_difference": np.full((size, size), np.nan),
        "joint_standard_error": np.full((size, size), np.nan),
        "conditional_counts_heston": np.zeros(size, dtype=int),
        "conditional_counts_local": np.zeros(size, dtype=int),
        "conditional_heston": np.full(size, np.nan),
        "conditional_local": np.full(size, np.nan),
        "conditional_difference": np.full(size, np.nan),
        "conditional_standard_error": np.full(size, np.nan),
        "conditional_supported": np.zeros(size, dtype=bool),
    }
    if failures.any():
        return result
    hb = np.searchsorted(cuts, heston, side="right")
    lb = np.searchsorted(cuts, local, side="right")
    hi = np.eye(size * size, dtype=float)[hb[:, 0] * size + hb[:, 1]]
    li = np.eye(size * size, dtype=float)[lb[:, 0] * size + lb[:, 1]]
    result["joint_counts_heston"] = hi.sum(axis=0).astype(int).reshape(size, size)
    result["joint_counts_local"] = li.sum(axis=0).astype(int).reshape(size, size)
    joint = sample_summary(li - hi)
    result["joint_difference"] = joint["mean"].reshape(size, size)
    result["joint_standard_error"] = joint["standard_error"].reshape(size, size)
    bh = heston[:, 1] > conditional_threshold
    bl = local[:, 1] > conditional_threshold
    for index in range(size):
        ah = hb[:, 0] == index
        al = lb[:, 0] == index
        nh, nl = int(ah.sum()), int(al.sum())
        result["conditional_counts_heston"][index] = nh
        result["conditional_counts_local"][index] = nl
        if min(nh, nl) < minimum_count:
            continue
        ph = np.sum(ah & bh) / nh
        pl = np.sum(al & bl) / nl
        ih = ((ah & bh).astype(float) - ph * ah) / (nh / count)
        il = ((al & bl).astype(float) - pl * al) / (nl / count)
        result["conditional_heston"][index] = ph
        result["conditional_local"][index] = pl
        result["conditional_difference"][index] = pl - ph
        result["conditional_standard_error"][index] = np.std(il - ih, ddof=1) / np.sqrt(count)
        result["conditional_supported"][index] = True
    return result
