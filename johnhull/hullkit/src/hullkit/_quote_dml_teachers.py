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
