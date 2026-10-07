"""Private Hull §30.1 local yield convexity; second-order, not exact pricing."""

import numpy as np
from scipy.optimize import brentq


def bond_value_derivatives(yield_rate, times, cashflows, frequency=1):
    """Cash bond price and its first two derivatives in compounded yield."""
    t, c = np.asarray(times, dtype=float), np.asarray(cashflows, dtype=float)
    if frequency <= 0 or 1 + yield_rate / frequency <= 0:
        raise ValueError("positive compounding base and frequency required")
    if t.ndim != 1 or not t.size or t.shape != c.shape or np.any(t < 0):
        raise ValueError("matching nonempty cashflows at nonnegative times required")
    base = 1 + yield_rate / frequency
    powers = frequency * t
    price_terms = c * base**-powers
    return {
        "price": float(price_terms.sum()),
        "first": float(np.sum(-t * price_terms / base)),
        "second": float(np.sum(t * (t + 1 / frequency) * price_terms / base**2)),
    }


def convexity_adjusted_yield(forward_yield, relative_volatility, fixing, first, second):
    """Hull 30.1: y_F - 1/2 y_F^2 sigma_y^2 T G''/G'.

    Relative yield vol supplies the local variance approximation. The output
    is a second-order estimate under the payment-forward measure, not a full
    distribution model for the terminal yield or an exact CMS pricing formula.
    """
    if relative_volatility < 0 or fixing < 0 or first == 0:
        raise ValueError("nonnegative volatility/time and nonzero first derivative required")
    return forward_yield - 0.5 * forward_yield**2 * relative_volatility**2 * fixing * second / first


def yield_linked_payment_pv(
    notional, forward_yield, relative_volatility, fixing, discount, times, cashflows, frequency=1
):
    """PV of a single yield-linked payment with the local convexity correction."""
    if notional < 0 or discount <= 0:
        raise ValueError("nonnegative notional and positive discount required")
    row = bond_value_derivatives(forward_yield, times, cashflows, frequency)
    expected = convexity_adjusted_yield(
        forward_yield, relative_volatility, fixing, row["first"], row["second"]
    )
    return dict(
        row,
        expected_yield=expected,
        pv=notional * discount * expected,
        unadjusted_pv=notional * discount * forward_yield,
    )


def cms_par_yield_approximation(discounts, accruals, times, frequency=1):
    """Construct the par coupon bond used for the CMS yield approximation.

    This constructs the bond with coupon equal to the current par swap rate.
    A fixed coupon bond's yield on a nonflat curve need not be the swap rate.
    Even the par bond construction does not make the future swap-rate/yield
    dynamics identical: that identification in the convexity correction is
    a local approximation.
    """
    p, a, t = map(lambda x: np.asarray(x, dtype=float), (discounts, accruals, times))
    if p.ndim != 1 or not p.size or p.shape != a.shape or p.shape != t.shape:
        raise ValueError("matching nonempty payment vectors required")
    if np.any(p <= 0) or np.any(a <= 0) or np.any(t <= 0) or frequency <= 0:
        raise ValueError("positive discounts/accruals/times/frequency required")
    swap = (1 - p[-1]) / float(a @ p)
    cash = swap * a
    cash[-1] += 1

    def residual(y):
        return bond_value_derivatives(y, t, cash, frequency)["price"] - 1

    lower = -frequency + 1e-8
    upper = max(1.0, swap + 1)
    while residual(upper) > 0:
        upper = 2 * upper + 1
    y = brentq(residual, lower, upper, xtol=1e-14)
    return {
        "swap_rate": swap,
        "bond_yield": y,
        "cashflows": cash,
        **bond_value_derivatives(y, t, cash, frequency),
    }


def convexity_taylor_decomposition(
    y, first, second, mean_y, variance, mean_price, forward_price, vol, expiry
):
    """Budget of the Ch30 appendix approximations, using supplied moments.

    E[(y_T-y_F)^2] is variance plus squared bias, not exactly variance.
    E[G(y_T)]-G(y_F) equals G'*bias + G''*second_moment/2 plus
    the omitted Taylor remainder. Hull's formula sets the mean-price change
    to zero, discards the remainder/bias squared, and substitutes the local
    lognormal yield variance y_F^2*sigma_y^2*T. Actual moments may come from
    independent quadrature or simulation; no terminal yield law is imposed.
    """
    if variance < 0:
        raise ValueError("nonnegative yield variance required")
    approximate = convexity_adjusted_yield(y, vol, expiry, first, second)
    bias = mean_y - y
    second_moment = variance + bias * bias
    linear = first * bias
    quadratic = 0.5 * second * second_moment
    price_change = mean_price - forward_price
    return {
        "bias": bias,
        "second_moment": second_moment,
        "variance_plus_bias_squared": variance + bias * bias,
        "local_second_moment": y * y * vol * vol * expiry,
        "linear_term": linear,
        "quadratic_term": quadratic,
        "mean_price_minus_forward": price_change,
        "omitted_price_remainder": price_change - linear - quadratic,
        "approximated_yield": approximate,
    }
