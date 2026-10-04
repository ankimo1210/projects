"""Private Hull §32.2 Gaussian/CIR bond options and coupon decomposition."""

import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from scipy.special import gammainc
from scipy.stats import ncx2, poisson

from ._forward_black import forward_black_price
from ._short_rate_models import cir_bond, mean_reversion_loading


def _contract(expiry, maturity, strike, discount, principal, kind):
    if (
        expiry < 0
        or maturity < expiry
        or strike < 0
        or min(discount, principal) <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError(
            "ordered nonnegative times, positive discount/principal and valid strike/kind required"
        )


def gaussian_bond_option(
    expiry, maturity, a, sigma, expiry_discount, bond_discount, strike, *, principal=1, kind="call"
):
    """Hull 32.10, total bond stddev from Vasicek/HW, including Ho–Lee a=0."""
    _contract(expiry, maturity, strike, expiry_discount, principal, kind)
    if min(a, sigma) < 0 or bond_discount <= 0:
        raise ValueError("nonnegative a/sigma and positive bond discount required")
    B = mean_reversion_loading(a, maturity - expiry)
    variance = sigma * sigma * B * B * mean_reversion_loading(2 * a, expiry)
    F = principal * bond_discount / expiry_discount
    if strike == 0:
        price = principal * bond_discount if kind == "call" else 0.0
    else:
        price = forward_black_price(expiry_discount, F, strike, math.sqrt(variance), 1, kind)
    return {"price": price, "variance": variance, "stddev": math.sqrt(variance), "forward": F}


def jamshidian_coupon_option(
    expiry, times, cashflows, strike, bond_at_exercise, zcb_option_price, *, kind="put"
):
    """Positive future coupon option via common monotone critical short rate.

    bond_at_exercise(rate,maturity) returns a unit-principal bond. The
    zcb_option_price(maturity,bond_strike,kind) callback must use the same
    model, current curve and expiry. Every underlying unit bond moves in
    the same direction. This does not apply to a two-factor basket or
    automatically replace a multicurve floating leg with a par bond.
    """
    t, c = np.asarray(times, dtype=float), np.asarray(cashflows, dtype=float)
    if (
        expiry < 0
        or t.ndim != 1
        or not t.size
        or t.shape != c.shape
        or np.any(t <= expiry)
        or np.any(c <= 0)
        or strike <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError("positive future cashflows/strike and valid kind required")

    def residual(rate):
        return float(c @ np.array([bond_at_exercise(rate, ti) for ti in t]) - strike)

    lo, hi = -0.1, 0.1
    while residual(lo) < 0:
        lo = 2 * lo - 0.1
    while residual(hi) > 0:
        hi = 2 * hi + 0.1
    critical = brentq(residual, lo, hi, xtol=1e-14)
    strikes = np.array([bond_at_exercise(critical, ti) for ti in t])
    components = c * np.array(
        [zcb_option_price(ti, ki, kind) for ti, ki in zip(t, strikes, strict=True)]
    )
    return {
        "price": float(components.sum()),
        "critical_rate": critical,
        "bond_strikes": strikes,
        "cash_strikes": c * strikes,
        "component_prices": components,
    }


def _chi_cdf(x, degrees, noncentrality):
    if x < 0:
        return 0.0
    if degrees > 0:
        return float(ncx2.cdf(x, degrees, noncentrality))
    # df=0 has an atom exp(-nc/2); scipy's df>0 interface cannot represent it.
    lam = noncentrality / 2
    if lam == 0:
        return 1.0
    limit = int(poisson.ppf(1 - 1e-14, lam)) + 1
    n = np.arange(1, limit + 1)
    return math.exp(-lam) + float(np.sum(poisson.pmf(n, lam) * gammainc(n, x / 2)))


def cir_bond_option(rate, a, b, sigma, expiry, maturity, strike, *, principal=1, kind="call"):
    """CIR option with the expiry-bond measure's noncentral chi-square law.

    The Q endpoint law multiplied by P0(expiry) is the wrong pricing law.
    Under the expiry measure k(t)=a+sigma²*B(expiry-t); g/q solve the
    corresponding transition ODEs. Exponential tilt gives the bond-weighted
    CDF; df=0 includes its absorbing-zero mass. sigma=0 is deterministic.
    """
    pt = cir_bond(rate, a, b, sigma, expiry)["price"]
    pu = cir_bond(rate, a, b, sigma, maturity)["price"]
    _contract(expiry, maturity, strike, pt, principal, kind)
    F = principal * pu / pt
    if strike == 0:
        return {"price": principal * pu if kind == "call" else 0.0}
    if expiry == 0 or sigma == 0 or maturity == expiry:
        return {"price": float(pt * max((1 if kind == "call" else -1) * (F - strike), 0))}
    interval = cir_bond(0, a, b, sigma, maturity - expiry)
    B = interval["B"]
    A = math.exp(interval["logA"])

    def ode(t, y):
        k = a + sigma * sigma * cir_bond(0, a, b, sigma, expiry - t)["B"]
        return [-k * y[0], sigma * sigma / 4 - k * y[1]]

    solution = solve_ivp(ode, (0, expiry), [1.0, 0.0], rtol=2e-12, atol=2e-14)
    if not solution.success:
        raise ValueError("expiry-measure transition failed")
    g, q = solution.y[:, -1]
    degrees = 4 * a * b / (sigma * sigma)
    nc = rate * g / q
    boundary = math.log(principal * A / strike) / B
    denominator = 1 + 2 * B * q
    laplace = denominator ** (-degrees / 2) * math.exp(-nc * B * q / denominator)
    first = (
        principal * A * laplace * _chi_cdf(boundary / (q / denominator), degrees, nc / denominator)
    )
    second = strike * _chi_cdf(boundary / q, degrees, nc)
    call = float(pt * (first - second))
    price = call if kind == "call" else call - principal * pu + strike * pt
    return {
        "price": price,
        "forward_scale": float(q),
        "degrees": degrees,
        "noncentrality": float(nc),
        "critical_rate": boundary,
    }
