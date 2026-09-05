"""Round 02 synthetic cash flows; independent of old generator/scorer."""

from __future__ import annotations

import math

import numpy as np


def schedule(t: float, frequency: int) -> tuple[np.ndarray, np.ndarray]:
    if not math.isfinite(t) or t <= 0 or t > 100:
        raise ValueError("maturity must be finite, positive and <= 100 years")
    if not math.isfinite(frequency) or frequency != int(frequency) or not 1 <= frequency <= 365:
        raise ValueError("frequency must be an integer in [1, 365]")
    times = np.arange(1, math.ceil(t * frequency) + 1, dtype=float) / frequency
    times = np.append(times[times < t - 1e-12], t)
    return times, np.diff(np.append(0.0, times))


def quote(row, discount) -> float:
    """Output percentage points for rates, price points for bonds."""
    t, kind = float(row["maturity_years"]), row["instrument_type"]
    if not math.isfinite(t) or not 0 < t <= 100:
        raise ValueError("maturity must be finite and in (0, 100]")
    dt = float(discount(t))
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("discount factor must be positive and finite")
    if kind == "deposit":
        return 100 * (1 / dt - 1) / t
    m = row["payment_frequency"]
    if kind == "ois_swap" and m != (1 if t <= 2 else 2):
        raise ValueError("OIS frequency conflicts with v2 contract")
    times, accrual = schedule(t, m)
    dfs = np.asarray(discount(times), dtype=float)
    if not np.isfinite(dfs).all() or (dfs <= 0).any():
        raise ValueError("cash-flow discount factors must be positive and finite")
    annuity = float(accrual @ dfs)
    if kind == "ois_swap":
        return 100 * (1 - dt) / annuity
    if kind == "bond":
        return 100 * (float(row["coupon_rate"]) * annuity + dt)
    raise ValueError(f"unknown instrument type: {kind}")


def pv(row, discount, trade_quote: float) -> float:
    t, kind = float(row["maturity_years"]), row["instrument_type"]
    if kind == "deposit":
        return 1e6 * ((1 + trade_quote / 100 * t) * float(discount(t)) - 1)
    if kind == "ois_swap":
        times, accrual = schedule(t, row["payment_frequency"])
        return 1e6 * (
            trade_quote / 100 * float(accrual @ discount(times)) - (1 - float(discount(t)))
        )
    if kind == "bond":
        return quote(row, discount) - trade_quote
    raise ValueError(kind)
