"""Private calibrated digital teachers for the RB-F07 quote-DML experiment.

One deterministic discount/forward curve drives a cash digital under GBM.
Quotes are five annual simple rates; zeros are continuously compounded.
Physical gradients are ordered spot first, then the five curve coordinates.
This is an offline synthetic experiment, with no torch or public API exports.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr

from . import _quote_risk as risk

QUOTE_KINDS = ("deposit", "fra", "swap", "swap", "swap")
QUOTE_TIMES = ((0.5,), (0.5, 1.0), (1.0, 2.0), (1.0, 2.0, 3.0), (1.0, 2.0, 3.0, 4.0, 5.0))
BASE_QUOTES = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])


@dataclass(frozen=True)
class Market:
    """Prepared calibration and dz/dq, with theta rows and quote columns."""

    quotes: np.ndarray
    calibration: risk.Calibration
    dz_dq: np.ndarray


def prepare_market(q):
    """Calibrate the fixed five-instrument single curve from annual decimal quotes.

    Negative rates are permitted when the instruments define positive discount
    ratios. Invalid quote dimensions and rank/nonconvergence fail explicitly.
    One Market can be shared by all contracts on the same market scenario.
    """
    values = np.asarray(q, dtype=float)
    if values.shape != (5,) or not np.isfinite(values).all():
        raise ValueError("five finite annual decimal quotes required")
    quotes = tuple(
        risk.Quote(kind, value, times)
        for kind, value, times in zip(QUOTE_KINDS, values, QUOTE_TIMES, strict=True)
    )
    calibration = risk.calibrate(quotes, interpolation="zero_linear")
    response = np.linalg.solve(calibration.jacobian, np.eye(5))
    return Market(values.copy(), calibration, response)


def _contract(spot, maturity, strike, sigma):
    values = np.asarray([spot, maturity, strike, sigma], dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("spot, maturity, strike and volatility must be finite and positive")
    return tuple(float(value) for value in values)


def _curve(market, maturity):
    calibration = market.calibration
    discounts, derivatives = risk.discount_factors(
        np.array([maturity]),
        calibration.times,
        calibration.zeros,
        interpolation=calibration.interpolation,
    )
    discount = float(discounts[0])
    if not np.isfinite(discount) or discount <= 0:
        raise ValueError("positive finite discount factor required")
    a_theta = -derivatives[0] / discount
    a_quote = market.dz_dq.T @ a_theta
    return discount, a_theta, a_quote


def analytic(market, spot, maturity, *, strike=100.0, sigma=0.2):
    """Return exact digital value and total spot/quote/zero sensitivities.

    The quote derivative includes discount and distribution effects. It fixes
    spot, strike, maturity and sigma while recalibrating the curve. Cash payout
    is one; the deterministic integrated rate is -log(P(0,T)). All derivatives
    are per raw decimal input unit, before any quote bp display factor.
    """
    spot, maturity, strike, sigma = _contract(spot, maturity, strike, sigma)
    discount, a_theta, a_quote = _curve(market, maturity)
    integrated_rate = -np.log(discount)
    v = sigma * np.sqrt(maturity)
    d2 = (np.log(spot / strike) + integrated_rate - v * v / 2) / v
    probability = float(ndtr(d2))
    density = float(np.exp(-d2 * d2 / 2) / np.sqrt(2 * np.pi))
    delta = discount * density / (spot * v)
    coefficient = discount * (-probability + density / v)
    g_theta = coefficient * a_theta
    g_quote = risk.quote_sensitivity(market.calibration, g_theta).per_unit
    return {
        "price": discount * probability,
        "g_quote": np.r_[delta, g_quote],
        "g_theta": np.r_[delta, g_theta],
        "discount": discount,
        "integrated_rate": float(integrated_rate),
        "a_quote": a_quote,
        "a_theta": a_theta,
        "amplification": market.calibration.amplification,
    }


def samples(market, spot, maturity, z, *, strike=100.0, sigma=0.2):
    """Return discounted pathwise teachers and explicit negative controls.

    z contains IID standard normals along its last axis. Price arrays match
    its shape, and gradient arrays append the six-component risk axis. LRM
    quote labels include the discount term -1; conditioning integrates the
    last half of the Brownian variance. Low expected hit or miss counts are
    flagged before interpreting MC means/SEs, not accepted as exact zero.
    """
    normals = np.asarray(z, dtype=float)
    if normals.ndim < 1 or normals.shape[-1] < 1 or not np.isfinite(normals).all():
        raise ValueError("finite nonempty standard-normal path arrays required")
    spot, maturity, strike, sigma = _contract(spot, maturity, strike, sigma)
    exact = analytic(market, spot, maturity, strike=strike, sigma=sigma)
    discount, a_quote = exact["discount"], exact["a_quote"]
    v = sigma * np.sqrt(maturity)
    log_mean = np.log(spot / strike) + exact["integrated_rate"] - v * v / 2
    payoff = discount * (log_mean + v * normals > 0)
    lrm = payoff[..., None] * np.concatenate(
        [
            (normals / (spot * v))[..., None],
            (-1 + normals / v)[..., None] * a_quote,
        ],
        axis=-1,
    )
    remaining = v / np.sqrt(2)
    b = (log_mean + remaining * normals) / remaining
    probability = ndtr(b)
    density = np.exp(-b * b / 2) / np.sqrt(2 * np.pi)
    conditional = np.concatenate(
        [
            (discount * density / (spot * remaining))[..., None],
            (discount * (-probability + density / remaining))[..., None] * a_quote,
        ],
        axis=-1,
    )
    naive = np.zeros_like(lrm)
    naive[..., 1:] = -payoff[..., None] * a_quote
    omitted = lrm + payoff[..., None] * np.r_[0.0, a_quote]
    hit_probability = exact["price"] / discount
    expected_hits = normals.shape[-1] * hit_probability
    expected_misses = normals.shape[-1] * (1 - hit_probability)
    return {
        "payoff": payoff,
        "lrm": lrm,
        "conditional_price": discount * probability,
        "conditional": conditional,
        "naive_pathwise": naive,
        "discount_omitted": omitted,
        "hit_probability": hit_probability,
        "expected_hits": expected_hits,
        "expected_misses": expected_misses,
        "mc_regime": "rare_event" if min(expected_hits, expected_misses) < 20 else "regular",
    }


def lrm_variance(market, spot, maturity, *, strike=100.0, sigma=0.2):
    """Return exact single-path LRM variance, spot first then raw quote Greeks.

    Truncated-normal second moments retain both the distribution score and
    discount derivative. Only negative variance from floating-point roundoff
    within 64 eps of the moment scale is clamped; larger negatives fail.
    """
    spot, maturity, strike, sigma = _contract(spot, maturity, strike, sigma)
    exact = analytic(market, spot, maturity, strike=strike, sigma=sigma)
    v = sigma * np.sqrt(maturity)
    d2 = (np.log(spot / strike) + exact["integrated_rate"] - v * v / 2) / v
    probability = exact["price"] / exact["discount"]
    density = np.exp(-d2 * d2 / 2) / np.sqrt(2 * np.pi)
    second_z = probability - d2 * density
    second = (
        exact["discount"] ** 2
        * np.r_[
            second_z / (spot * v) ** 2,
            (probability - 2 * density / v + second_z / v**2) * exact["a_quote"] ** 2,
        ]
    )
    mean_squared = exact["g_quote"] ** 2
    variance = second - mean_squared
    tolerance = 64 * np.finfo(float).eps * np.maximum(second, mean_squared)
    if np.any(variance < -tolerance):
        raise ArithmeticError("negative LRM variance beyond numerical roundoff")
    return np.maximum(variance, 0.0)
