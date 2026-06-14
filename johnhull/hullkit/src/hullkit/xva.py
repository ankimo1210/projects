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
