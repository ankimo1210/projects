"""Private Hull §34.3 currency legs and local nonstandard rate adjustments.

Leg conversion quotes domestic per foreign. The quanto correlation instead
quotes forward FX foreign per domestic, matching Hull §30.3; reversing FX
reverses that correlation. The CMS/timing composition is a local frozen
approximation, not a general collateral or stochastic multicurve model.
"""

import numpy as np

from ._quanto import quanto_forward
from ._timing_adjustment import timing_adjusted_payment
from ._yield_convexity import convexity_adjusted_yield


def currency_leg_value(receive_domestic_pv, pay_foreign_pv, spot_domestic_per_foreign):
    """PV domestic units; legs include any explicitly contracted principal."""
    if spot_domestic_per_foreign <= 0:
        raise ValueError("positive domestic/foreign spot required")
    return receive_domestic_pv - spot_domestic_per_foreign * pay_foreign_pv


def cip_fx_forward(spot_domestic_per_foreign, domestic_discounts, foreign_discounts):
    """Curve-implied domestic/foreign FX forwards under the specified CIP setup.

    An observed collateralized/basis FX curve cannot be replaced by arbitrary
    single-currency discounts without first making this identity consistent.
    """
    pd, pf = np.broadcast_arrays(
        np.asarray(domestic_discounts, dtype=float), np.asarray(foreign_discounts, dtype=float)
    )
    if spot_domestic_per_foreign <= 0 or np.any(pd <= 0) or np.any(pf <= 0):
        raise ValueError("positive spot and domestic/foreign discounts required")
    return spot_domestic_per_foreign * pf / pd


def fair_foreign_coupon_spread(
    receive_domestic_pv, foreign_base_pv, foreign_coupon_annuity, spot_domestic_per_foreign
):
    """Explicit linear coupon-spread solve; supplied annuity includes notionals."""
    if foreign_coupon_annuity <= 0 or spot_domestic_per_foreign <= 0:
        raise ValueError("positive foreign notional-annuity and domestic/foreign FX required")
    return (
        receive_domestic_pv / spot_domestic_per_foreign - foreign_base_pv
    ) / foreign_coupon_annuity


def adjusted_rate_coupon(
    *,
    notional,
    accrual,
    forward_rate,
    value_volatility,
    fixing,
    payment,
    payment_discount,
    first,
    second,
    rate_volatility=0.0,
    timing_correlation=0.0,
    quanto_fx_volatility=0.0,
    quanto_correlation=0.0,
    rate_frequency=1,
):
    """One rate-linked coupon: local CMS mean, frozen timing, forward-FX quanto.

    first/second are derivatives of the associated bond price wrt yield,
    supplied by the declared CMS/yield approximation. Quanto vol is forward
    FX foreign per domestic for this settlement; currency_leg_value uses the
    opposite spot quote. Zero-vol/correlation returns the corresponding base.
    """
    if notional < 0 or accrual <= 0:
        raise ValueError("nonnegative notional and positive accrual required")
    convexity = convexity_adjusted_yield(forward_rate, value_volatility, fixing, first, second)
    timing = timing_adjusted_payment(
        convexity,
        value_volatility,
        rate_volatility,
        timing_correlation,
        forward_rate,
        fixing,
        payment,
        payment_discount,
        frequency=rate_frequency,
    )
    adjusted = quanto_forward(
        timing["expected_value"], value_volatility, quanto_fx_volatility, quanto_correlation, fixing
    )
    quanto = quanto_forward(1.0, value_volatility, quanto_fx_volatility, quanto_correlation, fixing)
    return dict(
        convexity_adjusted_forward=convexity,
        timing_factor=timing["factor"],
        quanto_factor=quanto,
        adjusted_mean=adjusted,
        pv=notional * accrual * payment_discount * adjusted,
        unadjusted_pv=notional * accrual * payment_discount * forward_rate,
        approximation="local CMS and frozen timing/forward-FX loadings",
    )
