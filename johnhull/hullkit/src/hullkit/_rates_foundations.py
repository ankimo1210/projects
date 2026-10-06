"""Private Hull Ch4 rate conventions and cashflow-based foundational calculations."""

import numpy as np


def compounded_reference_rate(rates, days, *, basis=360):
    """Daily simple-interest factors compounded over caller-supplied day weights.

    A Friday fixing can carry days=3. Annualization uses basis/sum(days), not the
    number of observed fixings. This contains no calendar or fixing-date policy.
    """
    rates = np.asarray(rates, dtype=float)
    days = np.asarray(days, dtype=float)
    if (
        rates.ndim != 1
        or rates.shape != days.shape
        or not len(rates)
        or not np.isfinite(rates).all()
        or not np.isfinite(days).all()
        or not np.isfinite(basis)
        or basis <= 0
        or np.any(days <= 0)
    ):
        raise ValueError("paired fixings/day weights and positive basis required")
    factors = 1 + rates * days / basis
    if np.any(factors <= 0):
        raise ValueError("positive daily growth factors required")
    growth = float(np.prod(factors))
    return {
        "growth": growth,
        "days": float(days.sum()),
        "annualized_rate": (growth - 1) * basis / days.sum(),
    }


def compound_amount(principal, rate, years, *, frequency=None):
    """Growth under a continuous quote (None) or positive payments per year."""
    if not np.isfinite([principal, rate, years]).all() or min(principal, years) < 0:
        raise ValueError("finite rate and nonnegative principal/time required")
    if frequency is None:
        return float(principal * np.exp(rate * years))
    if not np.isfinite(frequency) or frequency <= 0 or 1 + rate / frequency <= 0:
        raise ValueError("positive frequency and periodic growth required")
    return float(principal * (1 + rate / frequency) ** (frequency * years))


def convert_rate(rate, source_frequency, target_frequency):
    """Convert annual quote frequency; None denotes continuous compounding."""
    from .rates import from_continuous, to_continuous

    if not np.isfinite(rate):
        raise ValueError("finite rate required")
    for frequency in [source_frequency, target_frequency]:
        if frequency is not None and (not np.isfinite(frequency) or frequency <= 0):
            raise ValueError("positive frequency required")
    if source_frequency is not None and 1 + rate / source_frequency <= 0:
        raise ValueError("positive source growth required")
    continuous = rate if source_frequency is None else to_continuous(rate, source_frequency)
    return continuous if target_frequency is None else from_continuous(continuous, target_frequency)


def zero_investment(principal, zero_rate, maturity):
    """Terminal amount for a continuous zero-rate investment, without coupons."""
    from .rates import discount_factor

    if not np.isfinite(principal) or principal < 0:
        raise ValueError("nonnegative principal required")
    return principal / discount_factor(maturity, ([maturity], [zero_rate]))


def _cash_vectors(times, cashflows):
    """Validate aligned finite cash dates with at least one nonzero payment."""
    t = np.asarray(times, dtype=float)
    cf = np.asarray(cashflows, dtype=float)
    if (
        t.ndim != 1
        or t.shape != cf.shape
        or not len(t)
        or not np.isfinite(t).all()
        or not np.isfinite(cf).all()
        or np.any(t < 0)
        or np.all(cf == 0)
    ):
        raise ValueError("aligned finite cash dates/payments required")
    return t, cf


def bond_quote(times, cashflows, zeros, *, face=100, frequency=2):
    """Cashflow PV/YTM and par annual coupon in cash per stated face amount.

    Par coupon uses equal coupon periods on the supplied dates; no irregular
    accrual schedule/day count is inferred in this Ch4 illustration.
    """
    from .rates import bond_price, bond_yield

    t, cf = _cash_vectors(times, cashflows)
    z = np.broadcast_to(np.asarray(zeros, dtype=float), t.shape)
    if (
        not np.isfinite(z).all()
        or not np.isfinite([face, frequency]).all()
        or min(face, frequency) <= 0
        or np.any(cf < 0)
        or t[-1] <= 0
    ):
        raise ValueError("positive face/frequency and positive bond payments required")
    df = np.exp(-z * t)
    price = bond_price(t, cf, z)
    return {
        "price": price,
        "yield": bond_yield(t, cf, price),
        "final_discount": df[-1],
        "coupon_annuity": df.sum(),
        "par_annual_coupon": frequency * face * (1 - df[-1]) / df.sum(),
    }
