"""CEV, Merton jump diffusion and variance gamma for Hull 11e GE §27.1.

European vanilla prices with continuous dividend yield. Inputs are scalar;
times are in years and rates/volatilities are annualized. These stylized
models are teaching implementations, not calibration or hedging engines.
"""

import math

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr, roots_genlaguerre
from scipy.stats import gamma as gamma_dist
from scipy.stats import ncx2, poisson

from . import bsm


def _inputs(spot, strike, rate, sigma, expiry, dividend_yield, kind):
    for name, value in (
        ("spot", spot),
        ("strike", strike),
        ("rate", rate),
        ("sigma", sigma),
        ("expiry", expiry),
        ("dividend_yield", dividend_yield),
    ):
        if not np.isscalar(value) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite scalar")
    if spot <= 0 or strike <= 0 or sigma < 0 or expiry < 0:
        raise ValueError("spot and strike must be positive; sigma and expiry nonnegative")
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")


def _bsm_price(spot, strike, rate, sigma, expiry, dividend_yield, kind):
    pricer = bsm.call_price if kind == "call" else bsm.put_price
    return float(pricer(spot, strike, rate, sigma, expiry, dividend_yield))


def cev_price(spot, strike, rate, sigma, expiry, beta, dividend_yield=0.0, *, kind="call"):
    """Hull §27.1 CEV European price via noncentral chi-square distributions.

    ``dS=(r-q)S dt + sigma S**beta dW``. The input ``sigma`` has units
    price**(1-beta)/sqrt(year); for a fixed spot volatility ``vol0``, use
    ``sigma=vol0*spot**(1-beta)``. At beta=1 the exact BSM limit is used.
    Within 1e-4 of beta=1 a BSM local-volatility limit avoids unstable
    noncentral-chi-square evaluations. ``0<beta<1`` has an absorbing zero
    boundary; ``beta>1`` follows Hull's
    stated closed-form branch. The latter's martingale-boundary subtleties
    are outside this teaching pricer's scope.
    """
    _inputs(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    if not np.isscalar(beta) or not math.isfinite(beta) or beta <= 0:
        raise ValueError("beta must be a finite positive scalar")
    if expiry == 0 or sigma == 0:
        return _bsm_price(spot, strike, rate, 0.0, expiry, dividend_yield, kind)
    if beta == 1:
        return _bsm_price(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    if abs(beta - 1) <= 1e-4:
        return _bsm_price(
            spot, strike, rate, sigma * spot ** (beta - 1), expiry, dividend_yield, kind
        )
    one_minus = 1 - beta
    drift = rate - dividend_yield
    z = 2 * drift * (beta - 1) * expiry
    v = sigma**2 * expiry * (math.expm1(z) / z if z != 0 else 1.0)
    denominator = one_minus**2 * v
    a = (strike * math.exp(-drift * expiry)) ** (2 * one_minus) / denominator
    c = spot ** (2 * one_minus) / denominator
    b = 1 / one_minus
    discounted_spot = spot * math.exp(-dividend_yield * expiry)
    discounted_strike = strike * math.exp(-rate * expiry)
    if beta < 1:
        call = discounted_spot * ncx2.sf(a, b + 2, c) - discounted_strike * ncx2.cdf(c, b, a)
        put = discounted_strike * ncx2.sf(c, b, a) - discounted_spot * ncx2.cdf(a, b + 2, c)
    else:
        call = discounted_spot * ncx2.sf(c, -b, a) - discounted_strike * ncx2.cdf(a, 2 - b, c)
        put = discounted_strike * ncx2.sf(a, 2 - b, c) - discounted_spot * ncx2.cdf(c, -b, a)
    return float(call if kind == "call" else put)


def merton_jump_price(
    spot,
    strike,
    rate,
    sigma,
    expiry,
    intensity,
    jump_mean,
    jump_vol,
    dividend_yield=0.0,
    *,
    kind="call",
):
    """Hull §27.1 Merton lognormal-jump European price by BSM series.

    ``N_T~Poisson(intensity*T)`` and each ``log(1+J)~N(jump_mean,jump_vol²)``.
    The drift subtracts ``intensity*E[J]``. The series is truncated when
    the reweighted Poisson upper tail is below about 1e-14.
    """
    _inputs(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    for name, value in (("intensity", intensity), ("jump_mean", jump_mean), ("jump_vol", jump_vol)):
        if not np.isscalar(value) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite scalar")
    if intensity < 0 or jump_vol < 0:
        raise ValueError("intensity and jump_vol must be nonnegative")
    if expiry == 0 or intensity == 0:
        return _bsm_price(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    jump_factor = math.exp(jump_mean + jump_vol**2 / 2)
    compensated = rate - intensity * (jump_factor - 1)
    weighted_mean = intensity * jump_factor * expiry
    upper = int(poisson.ppf(1 - 1e-14, weighted_mean)) + 1
    if upper > 10000:
        raise ValueError("intensity*expiry is too large for the teaching series")
    total = 0.0
    for count in range(upper + 1):
        adjusted_sigma = math.sqrt(sigma**2 + count * jump_vol**2 / expiry)
        adjusted_rate = compensated + count * math.log(jump_factor) / expiry
        total += poisson.pmf(count, weighted_mean) * _bsm_price(
            spot, strike, adjusted_rate, adjusted_sigma, expiry, dividend_yield, kind
        )
    return float(total)


def variance_gamma_price(
    spot,
    strike,
    rate,
    sigma,
    expiry,
    nu,
    theta,
    dividend_yield=0.0,
    *,
    kind="call",
):
    """Hull §27.1 VG European price by gamma-clock conditional quadrature.

    ``G_T~Gamma(T/nu,scale=nu)``, ``log S_T=log S_0+(r-q+omega)T+theta*G_T
    +sigma*W_{G_T}``, and ``omega=log(1-theta*nu-sigma²*nu/2)/nu``.
    Uses 96 generalized Gauss-Laguerre nodes, or gamma-density integration
    for large gamma shapes; ``nu=0`` is the BSM limit. An extreme shape uses
    that limit only when the random-clock drift is negligible.
    """
    _inputs(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    for name, value in (("nu", nu), ("theta", theta)):
        if not np.isscalar(value) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite scalar")
    if nu < 0:
        raise ValueError("nu must be nonnegative")
    if expiry == 0 or nu == 0:
        return _bsm_price(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    moment = 1 - theta * nu - sigma**2 * nu / 2
    if moment <= 0:
        raise ValueError("the VG exponential moment must exist")
    omega = math.log(moment) / nu
    shape = expiry / nu

    def conditional(clock):
        width = sigma * np.sqrt(clock)
        log_median = math.log(spot) + (rate - dividend_yield + omega) * expiry + theta * clock
        if sigma == 0:
            return (
                np.maximum(np.exp(log_median) - strike, 0)
                if kind == "call"
                else np.maximum(strike - np.exp(log_median), 0)
            )
        d2 = (log_median - math.log(strike)) / width
        forward = np.exp(log_median + width**2 / 2)
        if kind == "call":
            return forward * ndtr(d2 + width) - strike * ndtr(d2)
        return strike * ndtr(-d2) - forward * ndtr(-d2 - width)

    if shape > 1e7:
        if abs(theta) * math.sqrt(nu * expiry) > 1e-3:
            raise ValueError("gamma shape is too large for quadrature with material clock drift")
        return _bsm_price(spot, strike, rate, sigma, expiry, dividend_yield, kind)
    if shape >= 150:
        distribution = gamma_dist(a=shape, scale=nu)
        low, high = distribution.ppf((1e-13, 1 - 1e-13))
        value, error = quad(
            lambda clock: float(conditional(clock) * distribution.pdf(clock)),
            low,
            high,
            epsabs=1e-9,
            epsrel=1e-9,
        )
        if error > 1e-6:
            raise ArithmeticError("VG gamma quadrature did not converge")
    else:
        nodes, weights = roots_genlaguerre(96, shape - 1)
        value = np.dot(weights, conditional(nu * nodes)) / math.gamma(shape)
    return float(math.exp(-rate * expiry) * value)
