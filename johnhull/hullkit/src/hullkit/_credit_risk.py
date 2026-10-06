"""Private Hull Ch24 credit calculations. Probabilities are fractions, times years.

P denotes real-world/historical probabilities, Q pricing probabilities. Numerical
transformations do not convert between these measures; the caller supplies the
appropriate inputs. Exposure amounts inherit the supplied contract's money unit.
"""

import math

import numpy as np

from . import credit_curve


def _vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 1 or not np.isfinite(x).all():
        raise ValueError("finite nonempty vector required")
    return x


def _recovery(recovery):
    if not np.isfinite(recovery) or not 0 <= recovery <= 1:
        raise ValueError("recovery fraction in [0,1] required")


def constant_pd(hazard, maturity):
    if not np.isfinite([hazard, maturity]).all() or min(hazard, maturity) < 0:
        raise ValueError("nonnegative finite hazard/maturity required")
    return {"survival": math.exp(-hazard * maturity), "pd": -math.expm1(-hazard * maturity)}


def historical_pd(times, cumulative_pd, *, measure="P"):
    """Interval PDs and annual piecewise hazards from cumulative probabilities."""
    t, q = _vector(times), _vector(cumulative_pd)
    if (
        t.shape != q.shape
        or t[0] <= 0
        or np.any(np.diff(t) <= 0)
        or np.any(q < 0)
        or np.any(q >= 1)
        or np.any(np.diff(q) < 0)
        or measure not in ("P", "Q")
    ):
        raise ValueError(
            "increasing positive times, increasing finite PD in [0,1), and P/Q label required"
        )
    survival = 1 - q
    previous = np.r_[1, survival[:-1]]
    interval = previous - survival
    cumulative_hazard = -np.log1p(-q)
    forward = np.diff(np.r_[0, cumulative_hazard]) / np.diff(np.r_[0, t])
    curve = credit_curve.HazardCurve(tuple(t), tuple(forward))
    return {
        "survival": survival,
        "interval_pd": interval,
        "conditional_pd": interval / previous,
        "average_hazard": cumulative_hazard / t,
        "forward_hazard": forward,
        "curve": curve,
        "measure": measure,
    }


def spread_hazards(times, spreads, recovery):
    _recovery(recovery)
    t, s = _vector(times), _vector(spreads)
    if recovery == 1 or t.shape != s.shape or np.any(s < 0):
        raise ValueError("matching nonnegative spreads and recovery below one required")
    average = credit_curve.average_hazards_from_spreads(s, recovery)
    return {
        "average": average,
        "curve": credit_curve.forward_hazards_from_average(t, average),
        "measure": "Q",
    }


def bond_credit_table(
    curve, face, coupon_rate, maturity, rate, recovery, *, frequency=2, default_step=0.5
):
    """Direct coupon/principal survival and par-recovery PV under midpoint default.

    Default mass from each interval is placed at its midpoint, before any coupon
    at the same time. Coupons stop on default and recovery is recovery*face.
    This reproduces Hull's educational convention, not an ISDA schedule model.
    """
    _recovery(recovery)
    if (
        not np.isfinite([face, coupon_rate, maturity, rate, default_step]).all()
        or face < 0
        or maturity <= 0
        or default_step <= 0
        or frequency < 1
        or int(frequency) != frequency
    ):
        raise ValueError("finite bond terms and positive maturity/frequency/default step required")
    periods = round(maturity * frequency)
    defaults = round(maturity / default_step)
    if (
        periods < 1
        or defaults < 1
        or not math.isclose(periods / frequency, maturity, abs_tol=1e-10)
        or not math.isclose(defaults * default_step, maturity, abs_tol=1e-10)
    ):
        raise ValueError("maturity must contain complete coupon and default intervals")
    times = np.arange(1, periods + 1) / frequency
    cash = np.full(periods, face * coupon_rate / frequency)
    cash[-1] += face
    end = np.arange(1, defaults + 1) * default_step
    default_times = end - default_step / 2
    pd = curve.survival(end - default_step) - curve.survival(end)
    cumulative_pd = np.r_[0, np.cumsum(pd)]
    survival = 1 - cumulative_pd[np.searchsorted(default_times, times, side="right")]
    coupon_pv = cash * survival * np.exp(-rate * times)
    recovery_pv = recovery * face * pd * np.exp(-rate * default_times)
    promised = float(cash @ np.exp(-rate * times))
    forward_values = np.array(
        [
            sum(
                float(amount) * math.exp(-rate * (time - tau))
                for time, amount in zip(times, cash, strict=True)
                if time > tau
            )
            for tau in default_times
        ]
    )
    losses = (forward_values - recovery * face) * np.exp(-rate * default_times)
    value = float(coupon_pv.sum() + recovery_pv.sum())
    return {
        "cash_times": times,
        "cashflows": cash,
        "survival": survival,
        "default_times": default_times,
        "default_pd": pd,
        "surviving_cash_pv": coupon_pv,
        "recovery_pv": recovery_pv,
        "default_forward_values": forward_values,
        "discounted_default_losses": losses,
        "value": value,
        "promised_value": promised,
        "loss_pv": promised - value,
    }


def bond_curve_from_yields(
    maturities, yields, coupon_rate, rate, recovery, *, face=100, frequency=2, default_step=0.5
):
    """Existing Hull loss bootstrap with direct cashflow tables for comparison."""
    t, y = _vector(maturities), _vector(yields)
    if t.shape != y.shape:
        raise ValueError("matching maturity and yield vectors required")
    prices = np.array(
        [
            credit_curve.bond_price_from_yield(
                face, coupon_rate, float(time), float(yield_rate), frequency
            )
            for time, yield_rate in zip(t, y, strict=True)
        ]
    )
    result = credit_curve.bootstrap_from_bonds(
        prices, coupon_rate, t, rate, recovery, face, frequency, default_step
    )
    return {
        "curve": result.curve,
        "prices": prices,
        "risk_free": np.array(result.risk_free_prices),
        "loss_pv": np.array(result.expected_loss_pv),
        "measure": "Q",
    }
