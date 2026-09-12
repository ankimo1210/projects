"""Model quotes, present values and analytic Jacobians for the fitted curves."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from .curve import BSplineForwardCurve, ZeroCurve
from .instruments import Instrument, cash_flows


# --------------------------------------------------------------------------
# Generic (curve-agnostic) pricing
# --------------------------------------------------------------------------
def model_quote(inst: Instrument, curve: ZeroCurve) -> float:
    """Model quote in decimal units (rates) or points (bond prices)."""
    disc = curve.discount(inst.times)
    d_T = float(curve.discount(np.array([inst.maturity]))[0])
    if inst.instrument_type == "deposit":
        return (1.0 / d_T - 1.0) / inst.maturity
    if inst.instrument_type == "ois_swap":
        annuity = float(np.sum(inst.alphas * disc))
        return (1.0 - d_T) / annuity
    return float(np.sum(inst.amounts * disc) + 100.0 * d_T)


def dollar_duration(inst: Instrument, curve: ZeroCurve) -> float:
    """``-dP/dz`` for a parallel shift of the continuously compounded zero curve.

    For bonds this is per 100 face (points per unit rate); for rate instruments
    the residual is already a rate so the scale is 1.
    """
    if inst.instrument_type != "bond":
        return 1.0
    times, amounts = cash_flows(inst)
    disc = curve.discount(times)
    return float(np.sum(times * amounts * disc))


def rate_residual(inst: Instrument, curve: ZeroCurve) -> float:
    """Market-minus-model residual in yield-equivalent decimal rate units."""
    q = model_quote(inst, curve)
    if inst.is_rate:
        return inst.quote - q
    return (q - inst.quote) / dollar_duration(inst, curve)


def pv_receiver(inst: Instrument, curve: ZeroCurve) -> float:
    """PV of the receiver-fixed position at the market quote, in currency units.

    * deposit (notional 1e6): ``N * ((1 + r T) D(T) - 1)``.
    * OIS receiver-fixed (notional 1e6): ``N * (r sum(alpha_i D(t_i)) - (1 - D(T)))``.
    * bond (face 100): PV of coupons and principal.
    """
    disc = curve.discount(inst.times)
    d_T = float(curve.discount(np.array([inst.maturity]))[0])
    n = inst.notional
    if inst.instrument_type == "deposit":
        return n * ((1.0 + inst.quote * inst.maturity) * d_T - 1.0)
    if inst.instrument_type == "ois_swap":
        return n * (inst.quote * float(np.sum(inst.alphas * disc)) - (1.0 - d_T))
    return float(np.sum(inst.amounts * disc) + 100.0 * d_T)


def analytic_dv01(inst: Instrument, curve: ZeroCurve, bump: float = 1e-4) -> float:
    """``-dPV/dz * bump`` for a parallel zero shift (receiver position)."""
    disc = curve.discount(inst.times)
    d_T = float(curve.discount(np.array([inst.maturity]))[0])
    n = inst.notional
    if inst.instrument_type == "deposit":
        return n * (1.0 + inst.quote * inst.maturity) * inst.maturity * d_T * bump
    if inst.instrument_type == "ois_swap":
        return n * (inst.quote * float(np.sum(inst.alphas * inst.times * disc)) + inst.maturity * d_T) * bump
    times, amounts = cash_flows(inst)
    return float(np.sum(times * amounts * curve.discount(times))) * bump


# --------------------------------------------------------------------------
# Vectorised engine for the B-spline model (used inside the optimiser)
# --------------------------------------------------------------------------
@dataclass
class SplineResidualEngine:
    """Precomputed design matrices for fast residuals/Jacobians in the spline fit.

    Residuals are *market minus model* in yield-equivalent decimal rate units:
    ``q_mkt - q_model`` for deposits/OIS and ``(P_model - P_mkt) / DD`` for
    bonds, where ``DD = sum(t_i CF_i D_i)`` is the dollar duration.
    """

    curve: BSplineForwardCurve
    instruments: list[Instrument]

    def __post_init__(self) -> None:
        insts = self.instruments
        times = np.concatenate([i.times for i in insts]) if insts else np.zeros(0)
        self.times = times
        self.A = self.curve.design_integral(times) if len(times) else np.zeros((0, self.curve.n_basis))
        mats = np.array([i.maturity for i in insts], dtype=float)
        self.maturity = mats
        self.A_T = self.curve.design_integral(mats) if len(mats) else np.zeros((0, self.curve.n_basis))
        self.types = np.array([i.instrument_type for i in insts])
        self.quotes = np.array([i.quote for i in insts], dtype=float)
        rows, cols, alpha_vals, cf_vals, tcf_vals = [], [], [], [], []
        offset = 0
        for j, inst in enumerate(insts):
            m = len(inst.times)
            rows.extend([j] * m)
            cols.extend(range(offset, offset + m))
            alpha_vals.extend(inst.alphas.tolist())
            if inst.instrument_type == "bond":
                amounts = inst.amounts.copy()
                amounts[-1] += 100.0
                cf_vals.extend(amounts.tolist())
                tcf_vals.extend((amounts * inst.times).tolist())
            else:
                cf_vals.extend([0.0] * m)
                tcf_vals.extend([0.0] * m)
            offset += m
        shape = (len(insts), len(times))
        self.S_alpha = sparse.csr_matrix((alpha_vals, (rows, cols)), shape=shape)
        self.S_cf = sparse.csr_matrix((cf_vals, (rows, cols)), shape=shape)
        self.S_tcf = sparse.csr_matrix((tcf_vals, (rows, cols)), shape=shape)
        self.is_dep = self.types == "deposit"
        self.is_ois = self.types == "ois_swap"
        self.is_bond = self.types == "bond"

    def _discounts(self, coeffs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return np.exp(-(self.A @ coeffs)), np.exp(-(self.A_T @ coeffs))

    def model_quotes(self, coeffs: np.ndarray) -> np.ndarray:
        disc, d_T = self._discounts(coeffs)
        out = np.empty(len(self.instruments))
        annuity = self.S_alpha @ disc
        out[self.is_dep] = (1.0 / d_T[self.is_dep] - 1.0) / self.maturity[self.is_dep]
        out[self.is_ois] = (1.0 - d_T[self.is_ois]) / annuity[self.is_ois]
        out[self.is_bond] = (self.S_cf @ disc)[self.is_bond]
        return out

    def residuals(self, coeffs: np.ndarray) -> np.ndarray:
        disc, d_T = self._discounts(coeffs)
        q = self.model_quotes(coeffs)
        res = self.quotes - q
        if np.any(self.is_bond):
            dd = (self.S_tcf @ disc)[self.is_bond]
            res[self.is_bond] = (q[self.is_bond] - self.quotes[self.is_bond]) / dd
        return res

    def jacobian(self, coeffs: np.ndarray) -> np.ndarray:
        """``d residual / d coeffs`` (analytic)."""
        disc, d_T = self._discounts(coeffs)
        n_inst, n_b = len(self.instruments), self.curve.n_basis
        J = np.zeros((n_inst, n_b))
        DA = disc[:, None] * self.A  # D_i * A_i
        if np.any(self.is_dep):
            m = self.is_dep
            dq = (1.0 / d_T[m])[:, None] * self.A_T[m] / self.maturity[m][:, None]
            J[m] = -dq
        if np.any(self.is_ois):
            m = self.is_ois
            annuity = (self.S_alpha @ disc)[m]
            sum_aDA = (self.S_alpha @ DA)[m]
            dq = (d_T[m][:, None] * self.A_T[m] * annuity[:, None] + (1.0 - d_T[m])[:, None] * sum_aDA) / (annuity**2)[:, None]
            J[m] = -dq
        if np.any(self.is_bond):
            m = self.is_bond
            price = (self.S_cf @ disc)[m]
            dP = -(self.S_cf @ DA)[m]
            dd = (self.S_tcf @ disc)[m]
            dDD = -(self.S_tcf @ DA)[m]
            J[m] = dP / dd[:, None] - ((price - self.quotes[m]) / dd**2)[:, None] * dDD
        return J

    def dollar_durations(self, coeffs: np.ndarray) -> np.ndarray:
        disc, _ = self._discounts(coeffs)
        out = np.ones(len(self.instruments))
        out[self.is_bond] = (self.S_tcf @ disc)[self.is_bond]
        return out
