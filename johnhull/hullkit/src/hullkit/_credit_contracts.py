"""Private Hull Ch25 contract cashflows and single/index CDS calculations.

Rates are fractions per year; payment times are simplified year fractions,
not a calendar/day-count or ISDA legal-contract engine. Values state their
notional unit explicitly. New pricing APIs remain private.
"""

import math

import numpy as np

from ._credit_risk import _recovery


def basis_points_to_rate(basis_points):
    """Convert signed basis points to a rate fraction; one bp equals 0.0001."""
    if not np.isfinite(basis_points):
        raise ValueError("finite basis points required")
    return basis_points / 10000


def cds_contract_cashflows(
    notional, spread, maturity, *, frequency=4, default_time=None, recovery=0.4
):
    """Surviving coupons, last accrual and loss-of-par protection.

    Default at a scheduled date replaces that coupon with full-period accrual;
    no coupon is paid twice. A final shortened coupon period is supported.
    default_time beyond maturity leaves the contract alive through maturity.
    """
    _recovery(recovery)
    if (
        not np.isfinite([notional, spread, maturity]).all()
        or min(notional, spread) < 0
        or maturity <= 0
        or frequency < 1
        or int(frequency) != frequency
        or (default_time is not None and (not np.isfinite(default_time) or default_time < 0))
    ):
        raise ValueError(
            "nonnegative notional/spread/default time and positive maturity/frequency required"
        )
    times = np.arange(1, math.floor(maturity * frequency) + 1) / frequency
    if times.size == 0 or times[-1] < maturity:
        times = np.r_[times, maturity]
    active_default = default_time is not None and default_time <= maturity
    if active_default:
        times = np.r_[times[times < default_time], default_time]
    accrual = np.diff(np.r_[0, times])
    premium = notional * spread * accrual
    protection = np.zeros(times.size)
    if active_default:
        protection[-1] = notional * (1 - recovery)
    buyer = protection - premium
    return {
        "times": times,
        "premium": premium,
        "protection": protection,
        "buyer_cashflows": buyer,
        "seller_cashflows": -buyer,
        "regular_premium_rate": spread / frequency,
        "regular_premium": notional * spread / frequency,
    }


def cds_bond_basis(cds_spread, bond_yield, risk_free_rate):
    """CDS minus bond-yield spread, and yield after buying protection; all rates fractions."""
    if not np.isfinite([cds_spread, bond_yield, risk_free_rate]).all():
        raise ValueError("finite rates required")
    return {
        "basis": cds_spread - (bond_yield - risk_free_rate),
        "protected_yield": bond_yield - cds_spread,
    }


def cds_leg_table(curve, recovery, rate, maturity, *, frequency=1, start=0):
    """All row coefficients in Hull Tables25.1–5, per unit notional/spread."""
    from . import cds

    _recovery(recovery)
    if not np.isfinite([rate, maturity, start]).all() or start < 0:
        raise ValueError("finite rate/times and nonnegative start required")
    hazard = cds._as_curve(curve)
    times = cds._grid(start, maturity, frequency)
    dt = 1 / frequency
    mid = times - dt / 2
    survival = hazard.survival(times)
    pd = hazard.survival(times - dt) - survival
    end_df, mid_df = np.exp(-rate * times), np.exp(-rate * mid)
    annuity = dt * survival * end_df
    accrual_expected = dt / 2 * pd
    accrual = accrual_expected * mid_df
    protection_expected = (1 - recovery) * pd
    protection = protection_expected * mid_df
    binary = pd * mid_df
    duration = float(annuity.sum() + accrual.sum())
    return {
        "times": times,
        "mid_times": mid,
        "survival": survival,
        "interval_pd": pd,
        "end_discount": end_df,
        "mid_discount": mid_df,
        "annuity_rows": annuity,
        "accrual_expected": accrual_expected,
        "accrual_rows": accrual,
        "protection_expected": protection_expected,
        "protection_rows": protection,
        "binary_rows": binary,
        "annuity": float(annuity.sum()),
        "accrual": float(accrual.sum()),
        "protection": float(protection.sum()),
        "binary_protection": float(binary.sum()),
        "risky_duration": duration,
        "par_spread": float(protection.sum() / duration),
    }


def calibrated_cds(spread, recovery, rate, maturity, *, frequency=1):
    """Existing implied-hazard calibration with explicit row/leg output."""
    from . import cds

    if not np.isfinite(spread) or spread < 0:
        raise ValueError("nonnegative finite par spread required")
    _recovery(recovery)
    if recovery == 1:
        raise ValueError("spread-to-hazard calibration requires recovery below one")
    hazard = 0.0 if spread == 0 else cds.implied_hazard(spread, recovery, rate, maturity, frequency)
    result = cds_leg_table(hazard, recovery, rate, maturity, frequency=frequency)
    result["hazard"] = hazard
    return result


def recovery_recalibration(
    spread, recoveries, rate, maturity, *, frequency=1, contract_spread=None
):
    """Recalibrate hazard for each R at fixed market quote before comparing MTM."""
    from ._credit_risk import _vector

    recovery = _vector(recoveries)
    coupon = spread if contract_spread is None else contract_spread
    if not np.isfinite(coupon) or coupon < 0:
        raise ValueError("nonnegative contract premium required")
    tables = [
        calibrated_cds(spread, float(r), rate, maturity, frequency=frequency) for r in recovery
    ]
    return {
        "hazards": np.array([t["hazard"] for t in tables]),
        "par_spreads": np.array([t["par_spread"] for t in tables]),
        "binary_spreads": np.array([t["binary_protection"] / t["risky_duration"] for t in tables]),
        "buyer_values": np.array([t["protection"] - coupon * t["risky_duration"] for t in tables]),
    }


def index_premium(notional_per_name, spread, names, *, defaults=0):
    """Annual premium on equal live name notionals; integer default count reduces notional."""
    if (
        not np.isfinite([notional_per_name, spread, names, defaults]).all()
        or min(notional_per_name, spread) < 0
        or int(names) != names
        or int(defaults) != defaults
        or not 0 <= defaults <= names
    ):
        raise ValueError("nonnegative amounts/rate and integer name/default counts required")
    remaining = notional_per_name * (names - defaults)
    return {"remaining_notional": remaining, "annual_payment": remaining * spread}


def cds_index_value(
    curves, recoveries, notionals, rate, maturity, *, frequency=4, contract_spread=None
):
    """Sum individual protection/annuity legs; index spread is annuity-weighted.

    Curves are caller-supplied constituent pricing curves, not observed/current
    index constituents. Dependence is unnecessary for expected additive legs.
    """
    from ._credit_risk import _vector

    n = _vector(notionals)
    r = np.broadcast_to(np.asarray(recoveries, dtype=float), n.shape)
    if len(curves) != n.size or np.any(n < 0) or n.sum() <= 0:
        raise ValueError(
            "matching curves and nonnegative constituent notionals with positive sum required"
        )
    tables = [
        cds_leg_table(curve, float(recovery), rate, maturity, frequency=frequency)
        for curve, recovery in zip(curves, r, strict=True)
    ]
    annuity = n * np.array([t["risky_duration"] for t in tables])
    protection = float(n @ np.array([t["protection"] for t in tables]))
    duration = float(annuity.sum())
    par = protection / duration
    result = {
        "risky_duration": duration,
        "protection": protection,
        "par_spread": par,
        "annuity_weights": annuity / duration,
    }
    if contract_spread is not None:
        if not np.isfinite(contract_spread) or contract_spread < 0:
            raise ValueError("nonnegative finite index contract rate required")
        result["buyer_value"] = protection - contract_spread * duration
    return result


def fixed_coupon_quote(
    spread, coupon, recovery, rate, maturity, *, frequency=4, notional=100, quote_basis="actual360"
):
    """Ex25.1 quote calibration and fixed-coupon price/upfront, preserving unrounded rates.

    actual360 means the example's fixed 365/360 conversion, not a date-driven
    day count. buyer_upfront<0 means the buyer receives cash. D is risky premium
    annuity, not a bond-duration measure.
    """
    from . import cds

    if (
        not np.isfinite([spread, coupon, notional]).all()
        or min(spread, coupon, notional) < 0
        or quote_basis not in ("actual360", "year")
    ):
        raise ValueError("nonnegative spread/coupon/notional and supported quote basis required")
    multiplier = 365 / 360 if quote_basis == "actual360" else 1
    annual_spread, annual_coupon = spread * multiplier, coupon * multiplier
    result = calibrated_cds(annual_spread, recovery, rate, maturity, frequency=frequency)
    duration = result["risky_duration"]
    price = cds.fixed_coupon_price(annual_spread, annual_coupon, duration)
    return {
        "annual_spread": annual_spread,
        "annual_coupon": annual_coupon,
        "hazard": result["hazard"],
        "risky_duration": duration,
        "price_per_100": price,
        "buyer_upfront": cds.upfront_payment(annual_spread, annual_coupon, duration, notional),
    }


def forward_cds_contract(curve, recovery, rate, start, maturity, contract_spread, *, frequency=4):
    """Knockout forward CDS value per notional; annuity includes survival from time zero."""
    if not np.isfinite(contract_spread) or contract_spread < 0:
        raise ValueError("nonnegative finite contract spread required")
    legs = cds_leg_table(curve, recovery, rate, maturity, frequency=frequency, start=start)
    return {
        "start": start,
        "maturity": maturity,
        "contract_spread": contract_spread,
        "forward_spread": legs["par_spread"],
        "risky_annuity": legs["risky_duration"],
        "buyer_value": legs["protection"] - contract_spread * legs["risky_duration"],
    }


def cds_option_value(curve, recovery, rate, expiry, maturity, strike, volatility, *, frequency=4):
    """Black spread options per notional under the forward-annuity measure.

    Spread volatility is external; A already contains unconditional survival and
    discounting, so multiplying by survival again would count knockout twice.
    No front-end protection is included.
    """
    if not np.isfinite(volatility) or volatility < 0:
        raise ValueError("finite nonnegative volatility required")
    from . import cds

    forward = forward_cds_contract(
        curve, recovery, rate, expiry, maturity, strike, frequency=frequency
    )
    f, a = forward["forward_spread"], forward["risky_annuity"]
    return {
        "forward_spread": f,
        "risky_annuity": a,
        "payer": cds.cds_option(f, strike, volatility, expiry, a, kind="payer"),
        "receiver": cds.cds_option(f, strike, volatility, expiry, a, kind="receiver"),
    }


def knockout_spread_payoff(default_times, start, spreads, strike, annuity, *, kind="payer"):
    """Expiry spread payoff with default at/before start knocking out; amounts share annuity units."""
    default, spread, a = np.broadcast_arrays(default_times, spreads, annuity)
    if (
        not np.isfinite([start, strike]).all()
        or min(start, strike) < 0
        or np.isnan(default).any()
        or np.any(default < 0)
        or not np.isfinite(spread).all()
        or np.any(spread < 0)
        or not np.isfinite(a).all()
        or np.any(a < 0)
        or kind not in ("payer", "receiver", "forward")
    ):
        raise ValueError("nonnegative times/spreads/annuities and supported payoff kind required")
    payoff = a * (spread - strike)
    if kind == "payer":
        payoff = np.maximum(payoff, 0)
    elif kind == "receiver":
        payoff = np.maximum(-payoff, 0)
    return np.where(default > start, payoff, 0)


def total_return_swap_cashflows(
    notional, price_marks, coupons, floating_rates, year_fractions, *, spread=0.0025
):
    """Fixed initial-notional TRS: receiver gets price change + cash coupons minus financing.

    price_marks are asset value/initial notional (including the initial mark);
    coupons are cash amounts, rates annual fractions and intervals years. The
    caller supplies default/recovery marks; no fair-spread/CVA model is assumed.
    """
    marks = np.asarray(price_marks, dtype=float)
    dt = np.asarray(year_fractions, dtype=float)
    coupon = np.asarray(coupons, dtype=float)
    floating = np.asarray(floating_rates, dtype=float)
    if (
        dt.ndim != 1
        or dt.size == 0
        or marks.shape != (dt.size + 1,)
        or coupon.shape != dt.shape
        or floating.shape != dt.shape
        or not np.isfinite([notional, spread]).all()
        or notional < 0
        or not all(np.isfinite(v).all() for v in (marks, dt, coupon, floating))
        or np.any(dt <= 0)
        or np.any(marks < 0)
    ):
        raise ValueError(
            "matching finite periodic inputs, nonnegative notional/marks and positive periods required"
        )
    capital = notional * np.diff(marks)
    financing = notional * (floating + spread) * dt
    received = capital + coupon - financing
    return {
        "times": np.cumsum(dt),
        "capital_change": capital,
        "coupons": coupon,
        "financing": financing,
        "receiver_cashflows": received,
        "payer_cashflows": -received,
    }
