"""Counterparty credit exposure and XVA (A4 deep-dive).

Simulates the exposure of a long forward on a GBM underlying, computes the
expected exposure (EE), expected negative exposure (ENE) and potential future
exposure (PFE) profiles, and the credit / debit / funding value adjustments
(CVA / DVA / FVA). References: Gregory, *The xVA Challenge*; Hull Ch.24.
"""

from __future__ import annotations

import numpy as np

from . import mc


def forward_exposure(S0, r, sigma, K, T, n_steps=50, n_paths=50_000, rng=None):
    """Exposure of a long forward (delivery price K) on a GBM asset.

    Risk-neutral MtM at t is V_t = S_t - K e^{-r(T-t)}; the exposure to the
    counterparty is max(V_t, 0). Returns ``(t_grid, mtm)`` with mtm shape
    ``(n_paths, n_steps + 1)`` (positive and negative MtM, not yet floored).
    """
    paths = mc.simulate_gbm_paths(S0, r, sigma, T, n_steps, n_paths, rng=rng)
    t = np.linspace(0.0, T, n_steps + 1)
    mtm = paths - K * np.exp(-r * (T - t))
    return t, mtm


def expected_exposure(mtm):
    """EE(t) = E[max(V_t, 0)] across paths."""
    return np.maximum(mtm, 0.0).mean(axis=0)


def expected_negative_exposure(mtm):
    """ENE(t) = E[max(-V_t, 0)] across paths (drives DVA)."""
    return np.maximum(-mtm, 0.0).mean(axis=0)


def pfe(mtm, q=0.975):
    """Potential future exposure: the q-quantile of max(V_t, 0) across paths."""
    return np.quantile(np.maximum(mtm, 0.0), q, axis=0)


def cva(t, ee, hazard, recovery, r):
    """CVA = (1-R) Σ DF(t_i) · EE_mid · ΔPD over the grid (exposure ⟂ default).

    Trapezoidal in EE and the discount factor; ΔPD from a constant hazard.
    """
    surv = np.exp(-hazard * np.asarray(t))
    pd_inc = -np.diff(surv)
    df = np.exp(-r * np.asarray(t))
    ee_mid = 0.5 * (ee[:-1] + ee[1:])
    df_mid = 0.5 * (df[:-1] + df[1:])
    return float((1.0 - recovery) * np.sum(df_mid * ee_mid * pd_inc))


def dva(t, ene, own_hazard, own_recovery, r):
    """DVA = (1-R_own) Σ DF · ENE_mid · ΔPD_own — the mirror of CVA on our default."""
    return cva(t, ene, own_hazard, own_recovery, r)


def fva(t, ee, funding_spread, r):
    """Funding value adjustment ≈ spread · Σ DF(t_i) · EE_mid · Δt (simple EPE form)."""
    t = np.asarray(t)
    df = np.exp(-r * t)
    ee_mid = 0.5 * (ee[:-1] + ee[1:])
    df_mid = 0.5 * (df[:-1] + df[1:])
    dt = np.diff(t)
    return float(funding_spread * np.sum(df_mid * ee_mid * dt))


def default_probs_from_spreads(times, spreads, recovery):
    """Per-interval default probabilities from a credit-spread term structure (Hull §24.7).

    q_i = exp(−s(t_{i−1}) t_{i−1}/(1−R)) − exp(−s(t_i) t_i/(1−R)) with t_0 = 0.
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    times = np.asarray(times, dtype=float)
    spreads = np.asarray(spreads, dtype=float)
    if (
        times.shape != spreads.shape
        or times.ndim != 1
        or np.any(np.diff(times) <= 0.0)
        or times[0] <= 0.0
    ):
        raise ValueError("times must be positive, increasing, and match spreads")
    survival = np.concatenate([[1.0], np.exp(-spreads * times / (1.0 - recovery))])
    return -np.diff(survival)


def netting_set_exposure(values, netting=True):
    """Exposure of a set of trades (last axis): max(Σv, 0) with netting, Σ max(v, 0) without.

    Hull §24.7: trades worth +10, +30, −25 expose 40 without netting and 15 with it.
    """
    values = np.asarray(values, dtype=float)
    if netting:
        return np.maximum(values.sum(axis=-1), 0.0)
    return np.maximum(values, 0.0).sum(axis=-1)


def collateralized_exposure(value, lagged_value, threshold=0.0):
    """Exposure under a two-way collateral agreement with a cure period (Hull Example 24.4).

    Collateral held by each side is set from the portfolio value one cure period earlier:
    received C_r = max(V_lag − θ, 0), posted C_p = max(−V_lag − θ, 0). Exposure is the
    uncollateralised positive value plus any excess collateral posted:
    max(V − C_r, 0) + max(C_p − max(−V, 0), 0). Hull's four cases give 5, 0, 0, 5.
    """
    if threshold < 0.0:
        raise ValueError("threshold must be >= 0")
    value = np.asarray(value, dtype=float)
    lagged = np.asarray(lagged_value, dtype=float)
    received = np.maximum(lagged - threshold, 0.0)
    posted = np.maximum(-lagged - threshold, 0.0)
    return np.maximum(value - received, 0.0) + np.maximum(posted - np.maximum(-value, 0.0), 0.0)


def cva_single_payoff(no_default_value, recovery, default_probs):
    """CVA of one uncollateralised derivative paying off at T: (1−R) f_nd Σ q_i (Hull eq. 24.5)."""
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    total = np.sum(np.asarray(default_probs, dtype=float))
    return float((1.0 - recovery) * no_default_value * total)
