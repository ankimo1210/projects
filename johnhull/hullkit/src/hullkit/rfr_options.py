"""Bachelier and compounded-RFR option teachers for post-LIBOR markets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import quad
from scipy.stats import norm

FloatArray = NDArray[np.float64]


def _validate_option_inputs(
    forward: float,
    strike: float,
    normal_volatility: float,
    expiry: float,
    discount_factor: float,
    kind: str,
) -> None:
    values = (forward, strike, normal_volatility, expiry, discount_factor)
    if any(not np.isfinite(value) for value in values):
        raise ValueError("option inputs must be finite")
    if normal_volatility < 0.0 or expiry < 0.0 or discount_factor <= 0.0:
        raise ValueError("volatility/expiry/discount factor are invalid")
    if kind not in {"call", "put"}:
        raise ValueError("kind must be call or put")


def bachelier_price(
    forward: float,
    strike: float,
    normal_volatility: float,
    expiry: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Price a European rate option under the normal/Bachelier model."""

    _validate_option_inputs(forward, strike, normal_volatility, expiry, discount_factor, kind)
    standard_deviation = normal_volatility * np.sqrt(expiry)
    sign = 1.0 if kind == "call" else -1.0
    if standard_deviation == 0.0:
        return float(discount_factor * max(sign * (forward - strike), 0.0))
    d = (forward - strike) / standard_deviation
    return float(
        discount_factor
        * (sign * (forward - strike) * norm.cdf(sign * d) + standard_deviation * norm.pdf(d))
    )


def bachelier_delta(
    forward: float,
    strike: float,
    normal_volatility: float,
    expiry: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> float:
    """Forward delta with normal volatility held fixed."""

    _validate_option_inputs(forward, strike, normal_volatility, expiry, discount_factor, kind)
    standard_deviation = normal_volatility * np.sqrt(expiry)
    sign = 1.0 if kind == "call" else -1.0
    if standard_deviation == 0.0:
        if forward == strike:
            return float(0.5 * sign * discount_factor)
        return float(sign * discount_factor if sign * (forward - strike) > 0.0 else 0.0)
    d = (forward - strike) / standard_deviation
    return float(sign * discount_factor * norm.cdf(sign * d))


def gaussian_quadrature_price(
    forward: float,
    strike: float,
    normal_volatility: float,
    expiry: float,
    *,
    discount_factor: float = 1.0,
    kind: str = "call",
    absolute_tolerance: float = 1e-12,
) -> float:
    """High-precision adaptive Gaussian-integral teacher."""

    _validate_option_inputs(forward, strike, normal_volatility, expiry, discount_factor, kind)
    if not np.isfinite(absolute_tolerance) or absolute_tolerance <= 0.0:
        raise ValueError("absolute_tolerance must be finite and positive")
    if normal_volatility == 0.0 or expiry == 0.0:
        return bachelier_price(
            forward,
            strike,
            normal_volatility,
            expiry,
            discount_factor=discount_factor,
            kind=kind,
        )
    standard_deviation = normal_volatility * np.sqrt(expiry)
    threshold = (strike - forward) / standard_deviation
    if kind == "call":
        lower, upper = threshold, np.inf

        def integrand(z: float) -> float:
            return ((forward - strike) + standard_deviation * z) * norm.pdf(z)

    else:
        lower, upper = -np.inf, threshold

        def integrand(z: float) -> float:
            return ((strike - forward) - standard_deviation * z) * norm.pdf(z)

    value, _ = quad(integrand, lower, upper, epsabs=absolute_tolerance, epsrel=1e-12)
    return float(discount_factor * value)


@dataclass(frozen=True)
class CompoundedOptionResult:
    """Monte Carlo teacher output for an option on exact compounded RFR."""

    price: float
    standard_error: float
    compounded_rates: FloatArray


def compounded_rate_option_mc(
    simulated_daily_rates: ArrayLike,
    day_counts: ArrayLike,
    strike: float,
    *,
    basis: int = 360,
    discount_factor: float = 1.0,
    kind: str = "call",
) -> CompoundedOptionResult:
    """Price from simulated daily paths using exact, not continuous, compounding."""

    rates = np.asarray(simulated_daily_rates, dtype=float)
    counts = np.asarray(day_counts, dtype=float)
    if (
        rates.ndim != 2
        or rates.shape[0] < 2
        or counts.shape != (rates.shape[1],)
        or np.any(~np.isfinite(rates))
        or np.any(~np.isfinite(counts))
        or np.any(counts <= 0.0)
        or basis <= 0
    ):
        raise ValueError("daily rate paths/day counts/basis are invalid")
    if not np.isfinite(strike) or not np.isfinite(discount_factor) or discount_factor <= 0.0:
        raise ValueError("strike and discount factor are invalid")
    if kind not in {"call", "put"}:
        raise ValueError("kind must be call or put")
    factors = 1.0 + rates * counts[None, :] / basis
    if np.any(factors <= 0.0):
        raise ValueError("a simulated daily rate creates a non-positive factor")
    year_fraction = float(counts.sum() / basis)
    compounded = (np.prod(factors, axis=1) - 1.0) / year_fraction
    payoff = (
        np.maximum(compounded - strike, 0.0)
        if kind == "call"
        else np.maximum(strike - compounded, 0.0)
    )
    discounted = discount_factor * payoff
    return CompoundedOptionResult(
        price=float(discounted.mean()),
        standard_error=float(discounted.std(ddof=1) / np.sqrt(discounted.size)),
        compounded_rates=np.asarray(compounded),
    )
