"""Cash flows, instrument quote repricing, and receiver-fixed risk."""
from __future__ import annotations

import numpy as np


def regular_times(maturity, frequency):
    if not np.isfinite(maturity) or maturity <= 0 or not isinstance(frequency, (int, np.integer)) or frequency <= 0:
        raise ValueError("positive finite maturity and integer frequency required")
    times = np.arange(1, int(np.floor(maturity * frequency + 1e-9)) + 1, dtype=float) / frequency
    return times[times <= maturity + 1e-9]


def swap_schedule(maturity, frequency):
    times = regular_times(maturity, frequency)
    if len(times) == 0 or maturity - times[-1] > 1e-9:
        times = np.append(times, maturity)
    else:
        times[-1] = maturity
    return times, np.diff(np.r_[0, times])


def bond_cashflows(maturity, frequency, coupon, stub="prorated"):
    """Level coupons on valuation-anchored regular dates; principal at maturity.

    Regular coupons are level; an off-cycle terminal stub is prorated using its
    ACT/365F duration. The supplied convention does not specify stub amounts.
    Alternative terminal treatments are exposed for model-risk research.
    """
    times = regular_times(maturity, frequency)
    cash = np.full(len(times), 100 * coupon / frequency)
    if len(times) and abs(times[-1] - maturity) <= 1e-9:
        times[-1] = maturity
        cash[-1] += 100
    else:
        last = times[-1] if len(times) else 0.0
        extra = 100 * coupon * (maturity - last) if stub == "prorated" else (100 * coupon / frequency if stub == "full" else 0.0)
        times = np.append(times, maturity)
        cash = np.append(cash, 100 + extra)
    return times, cash


class PricingEngine:
    def __init__(self, frame, bond_stub="prorated"):
        self.frame = frame.reset_index(drop=True)
        self.types = self.frame.instrument_type.to_numpy()
        self.maturities = self.frame.maturity_years.to_numpy(float)
        schedules = []
        for r in self.frame.itertuples():
            if r.instrument_type == "deposit":
                schedules.append((np.array([r.maturity_years]), np.array([0.0])))
            elif r.instrument_type == "ois_swap":
                schedules.append(swap_schedule(r.maturity_years, int(r.payment_frequency)))
            elif r.instrument_type == "bond":
                schedules.append(bond_cashflows(r.maturity_years, int(r.payment_frequency), r.coupon_rate, bond_stub))
            else:
                raise ValueError(f"unsupported instrument type {r.instrument_type}")
        self.times = np.unique(np.concatenate([x[0] for x in schedules]))
        self.terminal = np.searchsorted(self.times, self.maturities)
        self.cash = np.zeros((len(self.frame), len(self.times)))
        for i, (ts, cash) in enumerate(schedules):
            self.cash[i, np.searchsorted(self.times, ts)] = cash

    def quotes_and_jacobian(self, beta, basis):
        exponent = -self.times * (basis @ beta) * 1e-4
        if np.max(abs(exponent)) > 700:
            raise ValueError("discount exponent outside safe floating-point range")
        disc = np.exp(exponent)
        jac_d = -(self.times * disc * 1e-4)[:, None] * basis
        dt = disc[self.terminal]
        jdt = jac_d[self.terminal]
        ann = self.cash @ disc
        jann = self.cash @ jac_d
        q = ann.copy()
        jac = jann.copy()
        dep = self.types == "deposit"
        swap = self.types == "ois_swap"
        q[dep] = (1 / dt[dep] - 1) / self.maturities[dep]
        jac[dep] = -jdt[dep] / (self.maturities[dep] * dt[dep]**2)[:, None]
        q[swap] = (1 - dt[swap]) / ann[swap]
        jac[swap] = (-jdt[swap] * ann[swap, None] - (1 - dt[swap, None]) * jann[swap]) / ann[swap, None]**2
        return q, jac

    def quote(self, curve):
        return self.quote_from_discount(curve.discount)

    def quote_from_discount(self, discount_function):
        """Price directly from D(t); no fitted zero-curve interpolation required."""
        d = np.asarray(discount_function(self.times), dtype=float)
        if d.shape != self.times.shape or not np.isfinite(d).all() or not (d > 0).all():
            raise ValueError("discount function must return positive finite values at all cash-flow times")
        dt = d[self.terminal]
        ann = self.cash @ d
        q = ann.copy()
        dep, swap = self.types == "deposit", self.types == "ois_swap"
        q[dep] = (1 / dt[dep] - 1) / self.maturities[dep]
        q[swap] = (1 - dt[swap]) / ann[swap]
        return q

    def fixed_cash(self):
        """Signed receiver-fixed cash flows; time-zero terms do not affect risk."""
        cash = self.cash.copy()
        initial = np.zeros(len(cash))
        for i, r in enumerate(self.frame.itertuples()):
            if r.instrument_type == "deposit":
                cash[i, self.terminal[i]] = 1e6 * (1 + r.normalized_quote * r.maturity_years)
                initial[i] = -1e6
            elif r.instrument_type == "ois_swap":
                cash[i] *= 1e6 * r.normalized_quote
                cash[i, self.terminal[i]] += 1e6
                initial[i] = -1e6
        return cash, initial

    def pv(self, curve, zero_bump=None):
        d = curve.discount(self.times)
        if zero_bump is not None:
            d = d * np.exp(-self.times * np.asarray(zero_bump))
        cash, initial = self.fixed_cash()
        return cash @ d + initial


def key_basis(times):
    """Linear hats with flat shoulders; weights sum to one for all t >= 0."""
    t = np.asarray(times, dtype=float)
    keys = np.array([2.0, 5.0, 10.0, 30.0])
    return np.column_stack([np.interp(t, keys, np.eye(4)[:, i]) for i in range(4)])


def risk_table(frame, curve):
    engine = PricingEngine(frame)
    h = 1e-4
    dv01 = (engine.pv(curve, -h) - engine.pv(curve, h)) / 2
    half = engine.pv(curve, -h / 2) - engine.pv(curve, h / 2)
    hats = key_basis(engine.times)
    keys = np.column_stack([(engine.pv(curve, -h * hats[:, i]) - engine.pv(curve, h * hats[:, i])) / 2 for i in range(4)])
    cash, _ = engine.fixed_cash()
    analytic = cash @ (engine.times * curve.discount(engine.times)) * h
    out = frame[["instrument_id", "instrument_type"]].copy()
    out["pv"] = engine.pv(curve)
    out["dv01"] = dv01
    for i, name in enumerate(("key_2y", "key_5y", "key_10y", "key_30y")):
        out[name] = keys[:, i]
    out["dv01_half_step"] = half
    out["dv01_first_order"] = analytic
    out["fd_relative_error"] = abs(dv01 - half) / np.maximum(abs(dv01), 1e-10)
    out["key_sum_relative_error"] = abs(keys.sum(axis=1) - dv01) / np.maximum(abs(dv01), 1e-10)
    return out
