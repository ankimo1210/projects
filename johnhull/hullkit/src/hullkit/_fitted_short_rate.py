"""Private Hull §32.1 Ho–Lee/HW curve fits and BDT/BK log-rate dynamics."""

import math

import numpy as np

from ._short_rate_models import mean_reversion_loading, vasicek_bond


def _domain(time, a, sigma):
    if min(time, a, sigma) < 0:
        raise ValueError("nonnegative time/a/sigma required")


def gaussian_curve_shift(time, a, sigma, forward):
    """phi=f0 + sigma² B(a,t)²/2 for r=phi+x; x is centered OU."""
    _domain(time, a, sigma)
    B = mean_reversion_loading(a, time)
    return forward(time) + 0.5 * sigma * sigma * B * B


def gaussian_curve_theta(time, a, sigma, forward, forward_derivative):
    """Hull 32.1/32.4 drift theta; a=0 is Ho–Lee theta=f0'+sigma²*t."""
    _domain(time, a, sigma)
    return (
        forward_derivative(time)
        + a * forward(time)
        + sigma * sigma * mean_reversion_loading(2 * a, time)
    )


def gaussian_fitted_bond(time, maturity, rate, a, sigma, log_discount, forward):
    """HW/Ho–Lee bond from a smooth input log-P0 curve, with log-P0(0)=0.

    Rate is the instantaneous short rate. The finite-period R used for tree
    discounting is a separate variable (§32.5). Negative Gaussian rates and
    input forwards are allowed. The curve's maturity derivative is f0.
    """
    _domain(time, a, sigma)
    if maturity < time:
        raise ValueError("maturity must be at least current time")
    B = mean_reversion_loading(a, maturity - time)
    variance_rate = sigma * sigma * mean_reversion_loading(2 * a, time)
    logP = (
        log_discount(maturity)
        - log_discount(time)
        - B * (rate - forward(time))
        - 0.5 * variance_rate * B * B
    )
    return math.exp(logP)


def gaussian_fitted_moments(time, maturity, rate, a, sigma, log_discount, forward):
    """Conditional joint Gaussian moments (r_T,integral_t^T r) under Q."""
    _domain(time, a, sigma)
    if maturity < time:
        raise ValueError("ordered times required")
    h = maturity - time
    B = mean_reversion_loading(a, h)
    phi = gaussian_curve_shift(time, a, sigma, forward)
    current = vasicek_bond(0, a, 0, sigma, time)
    terminal = vasicek_bond(0, a, 0, sigma, maturity)
    interval = vasicek_bond(0, a, 0, sigma, h)
    return {
        "mean_rate": gaussian_curve_shift(maturity, a, sigma, forward)
        + math.exp(-a * h) * (rate - phi),
        "variance_rate": interval["variance_rate"],
        "mean_integral": log_discount(time)
        - log_discount(maturity)
        + 0.5 * (terminal["variance_integral"] - current["variance_integral"])
        + B * (rate - phi),
        "variance_integral": interval["variance_integral"],
        "cov_rate_integral": interval["cov_rate_integral"],
    }


def bdt_mean_reversion(volatility, volatility_derivative):
    """BDT restriction a(t)=-sigma'(t)/sigma(t), unlike BK's free a(t)."""
    if volatility <= 0:
        raise ValueError("positive BDT volatility required for its derivative ratio")
    return -volatility_derivative / volatility


def log_rate_step(rate, theta, mean_reversion, volatility, delta, standard_normal):
    """Frozen-coefficient exact OU step for log r, then exp to positive r.

    BK can specify a and sigma independently. BDT's a can be negative when
    sigma rises. This is an exact step only for coefficients constant on
    the interval; no clipping/reflection or claim of a full fitted BK price.
    Theta belongs to log-rate drift, not the Gaussian level-rate theta.
    """
    r = np.asarray(rate, dtype=float)
    if np.any(r <= 0) or min(volatility, delta) < 0:
        raise ValueError("positive lognormal rates and nonnegative vol/time required")
    a = mean_reversion
    B = delta if a == 0 else -math.expm1(-a * delta) / a
    B2 = delta if a == 0 else -math.expm1(-2 * a * delta) / (2 * a)
    mean = np.log(r) * math.exp(-a * delta) + theta * B
    return np.exp(mean + volatility * math.sqrt(B2) * np.asarray(standard_normal))
