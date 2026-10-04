"""Private Hull §31.5 / TN14 coupled two-factor Gaussian short-rate model.

dr=(theta+u-a*r)dt+sigma1*dW1, du=-b*u*dt+sigma2*dW2.
Equilibrium uses theta=0; the separately named fitted model uses the
initial forward curve. sigma2 has rate/year/sqrt(year) units. Native kernels
handle a=b and singular correlation; TN14's transformed factors need a!=b.
"""

import math
from functools import lru_cache

import numpy as np
from scipy.integrate import quad_vec

from ._forward_black import forward_black_price
from ._short_rate_models import mean_reversion_loading


def _validate(a, b, sigma1, sigma2, rho, horizon):
    if min(a, b, sigma1, sigma2, horizon) < 0 or abs(rho) > 1:
        raise ValueError("nonnegative mean reversions/vols/time and correlation in [-1,1] required")


def two_factor_loadings(a, b, horizon):
    """B(year), C(year²), D(year); stable equal-mean-reversion limit."""
    if min(a, b, horizon) < 0:
        raise ValueError("nonnegative a/b/time required")
    h = horizon
    B = mean_reversion_loading(a, h)
    gap = abs(a - b)
    D = math.exp(-min(a, b) * h) * (h if gap == 0 else -math.expm1(-gap * h) / gap)
    if gap * h < 1e-6:
        # Symmetric divided difference: midpoint limit error is quadratic in gap*h.
        k = (a + b) / 2
        x = k * h
        if x < 0.001:
            C = h * h * sum((-x) ** n * (n + 1) / math.factorial(n + 2) for n in range(9))
        else:
            C = (-math.expm1(-x) - x * math.exp(-x)) / (k * k)
    else:
        C = (mean_reversion_loading(b, h) - B) / (a - b)
    return {"B": B, "C": C, "D": D}


def _kernels(z, a, b, sigma1, sigma2):
    row = two_factor_loadings(a, b, z)
    return np.array([sigma1 * math.exp(-a * z), 0, sigma1 * row["B"]]), np.array(
        [sigma2 * row["D"], sigma2 * math.exp(-b * z), sigma2 * row["C"]]
    )


@lru_cache(maxsize=256)
def _covariance_tuple(a, b, sigma1, sigma2, rho, horizon):
    if horizon == 0:
        return (0.0,) * 9

    def integrand(z):
        x, y = _kernels(z, a, b, sigma1, sigma2)
        combined = x + rho * y
        return np.outer(combined, combined) + (1 - rho * rho) * np.outer(y, y)

    cov = quad_vec(integrand, 0, horizon, epsabs=2e-13, epsrel=2e-12)[0]
    return tuple(((cov + cov.T) / 2).ravel())


def two_factor_moments(rate, level, a, b, sigma1, sigma2, rho, horizon):
    """Equilibrium means/covariance for (r_T,u_T,integral r), conditional today."""
    _validate(a, b, sigma1, sigma2, rho, horizon)
    row = two_factor_loadings(a, b, horizon)
    mean = np.array(
        [
            math.exp(-a * horizon) * rate + row["D"] * level,
            math.exp(-b * horizon) * level,
            row["B"] * rate + row["C"] * level,
        ]
    )
    covariance = np.array(_covariance_tuple(a, b, sigma1, sigma2, rho, horizon)).reshape(3, 3)
    return {"mean": mean, "covariance": covariance, **row}


def equilibrium_bond(rate, level, a, b, sigma1, sigma2, rho, horizon):
    """Theta=0 P=exp(-B*r-C*u+Var(integral)/2); no arbitrary market shift."""
    row = two_factor_moments(rate, level, a, b, sigma1, sigma2, rho, horizon)
    return math.exp(-row["mean"][2] + row["covariance"][2, 2] / 2)


def two_factor_shift(time, a, b, sigma1, sigma2, rho):
    """TN14 psi=V'/2 and psi', excluding the market forward f0."""
    _validate(a, b, sigma1, sigma2, rho, time)
    row = two_factor_loadings(a, b, time)
    x, y = sigma1 * row["B"], sigma2 * row["C"]
    dx, dy = sigma1 * math.exp(-a * time), sigma2 * row["D"]
    return {
        "psi": 0.5 * ((x + rho * y) ** 2 + (1 - rho * rho) * y * y),
        "psi_prime": x * dx + y * dy + rho * (x * dy + y * dx),
    }


def curve_fitted_theta(time, a, b, sigma1, sigma2, rho, forward, forward_derivative, *, u0=0):
    """theta=d(f0+psi)/d maturity + a*(f0+psi), minus u0*exp(-b*t).

    TN14 writes F_t(0,t); the derivative required here is of the initial
    curve in its maturity argument. A literal first-argument partial does
    not fit the initial curve. u0!=0 is an explicitly centered extension.
    """
    shift = two_factor_shift(time, a, b, sigma1, sigma2, rho)
    return (
        forward_derivative(time)
        + shift["psi_prime"]
        + a * (forward(time) + shift["psi"])
        - u0 * math.exp(-b * time)
    )


def curve_fitted_bond(
    time, maturity, rate, level, a, b, sigma1, sigma2, rho, log_discount, forward, *, u0=0
):
    """TN14 fitted P0 ratio, conditional on both observed r and u.

    u0=0 is TN14's initial setting; it does not require u_t=0 later. The
    explicit u0 extension centers the level and theta together. The curve
    must supply f0 at time; theta additionally needs its maturity derivative.
    """
    if time < 0 or maturity < time:
        raise ValueError("ordered nonnegative times required")
    h = maturity - time
    row = two_factor_loadings(a, b, h)

    def variance(t):
        return two_factor_moments(0, 0, a, b, sigma1, sigma2, rho, t)["covariance"][2, 2]

    phi = forward(time) + two_factor_shift(time, a, b, sigma1, sigma2, rho)["psi"]
    logP = (
        log_discount(maturity)
        - log_discount(time)
        - row["B"] * (rate - phi)
        - row["C"] * (level - u0 * math.exp(-b * time))
        + 0.5 * (variance(h) - variance(maturity) + variance(time))
    )
    return math.exp(logP)


def tn14_gamma_eta(time, maturity, a, b, sigma1, sigma2, rho):
    """All six TN14 appendix gamma kernels and eta, also valid at a=b."""
    if time < 0 or maturity < time:
        raise ValueError("ordered nonnegative times required")
    _validate(a, b, sigma1, sigma2, rho, maturity)
    h = maturity - time

    def kernels(z):
        row = two_factor_loadings(a, b, z)
        return np.array([math.exp(-a * z) * row["D"], row["B"] * row["C"], row["C"] ** 2])

    late = quad_vec(kernels, h, maturity, epsabs=2e-13, epsrel=2e-12)[0]
    early = quad_vec(kernels, 0, time, epsabs=2e-13, epsrel=2e-12)[0]

    def variance(t):
        return two_factor_moments(0, 0, a, b, sigma1, sigma2, rho, t)["covariance"][2, 2]

    eta = (
        0.5 * (variance(maturity) - variance(time) - variance(h))
        - two_factor_loadings(a, b, h)["B"]
        * two_factor_shift(time, a, b, sigma1, sigma2, rho)["psi"]
    )
    return {
        "gamma": np.array([late[0], late[1], early[0], early[1], late[2], early[2]]),
        "eta": eta,
    }


def forward_rate_volatility(a, b, sigma1, sigma2, rho, horizon):
    """Instantaneous forward-rate vol by maturity; TN14 hump parameters."""
    _validate(a, b, sigma1, sigma2, rho, horizon)
    x = sigma1 * math.exp(-a * horizon)
    y = sigma2 * two_factor_loadings(a, b, horizon)["D"]
    return math.sqrt((x + rho * y) ** 2 + (1 - rho * rho) * y * y)


def two_factor_zcb_option(
    expiry,
    maturity,
    a,
    b,
    sigma1,
    sigma2,
    rho,
    expiry_discount,
    bond_discount,
    strike,
    *,
    principal=1,
    kind="call",
):
    """Exact Gaussian forward-bond option, including TN14 appendix variance."""
    _validate(a, b, sigma1, sigma2, rho, expiry)
    if (
        maturity < expiry
        or strike < 0
        or min(expiry_discount, bond_discount) <= 0
        or principal <= 0
        or kind not in ("call", "put")
    ):
        raise ValueError("valid future bond/discounts/principal/strike/kind required")
    row = two_factor_loadings(a, b, maturity - expiry)
    load = np.array([row["B"], row["C"]])
    cov = two_factor_moments(0, 0, a, b, sigma1, sigma2, rho, expiry)["covariance"][:2, :2]
    variance = max(float(load @ cov @ load), 0)
    F = principal * bond_discount / expiry_discount
    if strike == 0:
        price = principal * bond_discount if kind == "call" else 0.0
    else:
        price = forward_black_price(
            expiry_discount, F, strike, math.sqrt(variance / expiry) if expiry else 0, expiry, kind
        )
    return {"price": price, "variance": variance, "forward": F}


def two_factor_coupon_approximation(
    expiry,
    times,
    cashflows,
    a,
    b,
    sigma1,
    sigma2,
    rho,
    expiry_discount,
    bond_discounts,
    strike,
    *,
    kind="call",
):
    """TN14 first-two-moment lognormal approximation, not an exact basket law."""
    _validate(a, b, sigma1, sigma2, rho, expiry)
    t, c, p = map(lambda x: np.asarray(x, dtype=float), (times, cashflows, bond_discounts))
    if (
        t.ndim != 1
        or not t.size
        or t.shape != c.shape
        or t.shape != p.shape
        or np.any(t <= expiry)
        or np.any(c <= 0)
        or np.any(p <= 0)
        or expiry_discount <= 0
        or strike < 0
        or kind not in ("call", "put")
    ):
        raise ValueError(
            "matching positive future cashflows/discounts and valid strike/kind required"
        )
    rows = [two_factor_loadings(a, b, float(ti) - expiry) for ti in t]
    load = np.array([[row["B"], row["C"]] for row in rows])
    covariance = two_factor_moments(0, 0, a, b, sigma1, sigma2, rho, expiry)["covariance"][:2, :2]
    cross = load @ covariance @ load.T
    amounts = c * p / expiry_discount
    first = float(amounts.sum())
    second = float(amounts @ np.exp(cross) @ amounts)
    variance = max(math.log(second / (first * first)), 0)
    if strike == 0:
        price = expiry_discount * first if kind == "call" else 0.0
    else:
        price = forward_black_price(
            expiry_discount,
            first,
            strike,
            math.sqrt(variance / expiry) if expiry else 0,
            expiry,
            kind,
        )
    return {
        "price": price,
        "first_moment": first,
        "second_moment": second,
        "matched_log_variance": variance,
        "log_bond_covariance": cross,
    }


def tn14_transformed_factors(a, b, sigma1, sigma2, rho):
    """y=r+u/(b-a); undefined at a=b, while native moments remain valid."""
    _validate(a, b, sigma1, sigma2, rho, 0)
    if a == b:
        raise ValueError("transformed factors require a!=b; use native kernels")
    shifted = sigma2 / (b - a)
    sigma_y = math.sqrt((sigma1 + rho * shifted) ** 2 + (1 - rho * rho) * shifted * shifted)
    if sigma_y <= 16 * np.finfo(float).eps * (abs(sigma1) + abs(shifted)):
        sigma_y = 0.0
    correlation = None if sigma_y == 0 or sigma2 == 0 else (rho * sigma1 + shifted) / sigma_y
    return {"sigma_y": sigma_y, "correlation_y_u": correlation}
