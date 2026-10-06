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


def periodic_bond_yield(times, cashflows, price, *, frequency):
    """Positive-cashflow bond yield as an annual quote at a specified frequency."""
    from scipy.optimize import brentq

    t, cf = _cash_vectors(times, cashflows)
    if (
        not np.isfinite([price, frequency]).all()
        or min(price, frequency) <= 0
        or np.any(cf < 0)
        or np.any(t <= 0)
    ):
        raise ValueError("positive price/frequency and future nonnegative payments required")

    def error(y):
        return np.dot(cf, (1 + y / frequency) ** (-frequency * t)) - price

    upper = 1.0
    while error(upper) > 0:
        upper = 2 * upper + 1
    return brentq(error, -frequency + frequency * 1e-8, upper, xtol=1e-13)


def bootstrap_piecewise_zero(instruments):
    """Sequential bond calibration with linear zeros and flat endpoint extrapolation.

    Each instrument is (cash_dates,cash_amounts,price), sorted by its last date.
    Coupons between the last known node and the new node depend on the new zero
    and are solved jointly for that segment. All cash payments are nonnegative.
    """
    from scipy.optimize import brentq

    parsed = []
    for times, cashflows, price in instruments:
        t, cf = _cash_vectors(times, cashflows)
        if (
            np.any(np.diff(t) <= 0)
            or t[0] <= 0
            or np.any(cf < 0)
            or not np.isfinite(price)
            or price <= 0
        ):
            raise ValueError(
                "ordered future cash dates, nonnegative payments and positive price required"
            )
        parsed.append((t, cf, price))
    nodes = []
    zeros = []
    for t, cf, price in sorted(parsed, key=lambda item: item[0][-1]):
        maturity = float(t[-1])
        if nodes and maturity <= nodes[-1]:
            raise ValueError("distinct instrument maturity nodes required")

        def error(z, t=t, cf=cf, price=price, maturity=maturity):
            rates = np.interp(t, [*nodes, maturity], [*zeros, z])
            return np.dot(cf, np.exp(-rates * t)) - price

        lo, hi = -0.25, 0.25
        for _ in range(12):
            if error(lo) * error(hi) <= 0:
                break
            lo *= 2
            hi *= 2
        else:
            raise ValueError("no positive-discount curve fits this segment")
        zero = brentq(error, lo, hi, xtol=1e-13)
        nodes.append(maturity)
        zeros.append(zero)
    return np.array(nodes), np.array(zeros)


def curve_forward(start, end, curve):
    """Continuous forward and growth of the two zero-bond replication cash amounts."""
    from .rates import discount_factor

    if not np.isfinite([start, end]).all() or start < 0 or end <= start:
        raise ValueError("0<=start<end required")
    p1 = discount_factor(start, curve)
    p2 = discount_factor(end, curve)
    return {
        "continuous_rate": np.log(p1 / p2) / (end - start),
        "start_growth": 1 / p1,
        "end_growth": 1 / p2,
        "forward_discount": p2 / p1,
    }


def instantaneous_curve_forward(time, curve, *, bump=1e-5):
    """Instantaneous forward following supplied linear zeros, averaged at a knot."""
    from .rates import instantaneous_forward

    return instantaneous_forward(time, curve, bump=bump)


def fra_settlement(notional, fixed_rate, observed_rate, accrual, *, receive="fixed"):
    """FRA cash at period end or prepaid at the observed simple-rate discount.

    observed_rate is known at fixing; this realized cashflow is distinct from a
    pre-fixing model value. Principal is not exchanged by the FRA.
    """
    if (
        not np.isfinite([notional, fixed_rate, observed_rate, accrual]).all()
        or notional < 0
        or accrual <= 0
        or 1 + observed_rate * accrual <= 0
        or receive not in ("fixed", "floating")
    ):
        raise ValueError("valid notional/accrual/simple growth and receive direction required")
    cash = (1 if receive == "fixed" else -1) * notional * accrual * (fixed_rate - observed_rate)
    return {"end_payment": cash, "advance_payment": cash / (1 + observed_rate * accrual)}


def fra_contract_value(
    notional, fixed_rate, forward_rate, start, end, discount_zero, *, receive="fixed"
):
    """Pre-fixing FRA PV with period-simple rates and a continuous payment-date zero."""
    from .rates import fra_value

    if not np.isfinite([start, end, discount_zero]).all() or start < 0 or end <= start:
        raise ValueError("0<=start<end and finite discount zero required")
    fra_settlement(notional, fixed_rate, forward_rate, end - start, receive=receive)
    return (1 if receive == "fixed" else -1) * fra_value(
        notional, fixed_rate, forward_rate, start, end, discount_zero
    )


def bond_sensitivities(times, cashflows, yield_quote, *, frequency=None):
    """PV weights, duration, dollar risk and convexity in the supplied yield quote.

    None is continuous; positive frequency gives a periodic annual quote.
    dv01 is positive -dB/dy times 1bp, not an actual nonlinear 1bp price move.
    Cashflow dates may be unordered; positive total PV is needed for normalization.
    """
    t, cf = _cash_vectors(times, cashflows)
    if not np.isfinite(yield_quote):
        raise ValueError("finite yield required")
    if frequency is None:
        growth = 1.0
        pv = cf * np.exp(-yield_quote * t)
        second = t**2
    else:
        if not np.isfinite(frequency) or frequency <= 0 or 1 + yield_quote / frequency <= 0:
            raise ValueError("positive frequency and growth required")
        growth = 1 + yield_quote / frequency
        pv = cf * growth ** (-frequency * t)
        second = (t**2 + t / frequency) / growth**2
    price = float(pv.sum())
    if price <= 0:
        raise ValueError("positive total present value required")
    weights = pv / price
    duration = float(t @ weights)
    modified = duration / growth
    convexity = float(second @ weights)
    return {
        "price": price,
        "cash_present_values": pv,
        "weights": weights,
        "macaulay": duration,
        "modified": modified,
        "dollar_duration": price * modified,
        "dv01": price * modified * 1e-4,
        "convexity": convexity,
        "price_gamma": price * convexity,
    }
