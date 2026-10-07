"""Private Hull §32.7 external curve/vol shocks with one-factor pricing.

Curve shocks rebuild the fitted discount environment, keeping a and absolute
HW sigma fixed. Vol shocks keep the curve fixed. This is not recalibration
risk against option quotes and does not add stochastic pricing factors.
"""

import math

import numpy as np

from ._ir_hedging import rate_hedge_report, volatility_hedge_report
from ._short_rate_calibration import european_swaption


def gaussian_environment_price(quotes, curve_times, zero_rates, a, vol_knots, sigmas):
    """Portfolio on continuously compounded, linearly interpolated zero rates."""
    t, z = np.asarray(curve_times, dtype=float), np.asarray(zero_rates, dtype=float)
    if t.ndim != 1 or not t.size or z.shape != t.shape or np.any(t <= 0) or np.any(np.diff(t) <= 0):
        raise ValueError("positive increasing curve times and matching zero rates required")

    def curve(time):
        return math.exp(-time * float(np.interp(time, t, z)))

    return sum(european_swaption(q, curve, a, vol_knots, sigmas)["price"] for q in quotes)


def _vol_hedges(value, sigmas, directions, bump):
    """Central vega inside the domain; second-order one-sided vega at zero."""
    s = np.asarray(sigmas, dtype=float)
    p = np.asarray(directions, dtype=float)
    if bump <= 0 or p.ndim != 2 or p.shape[0] != s.size:
        raise ValueError("positive vol bump and matching direction rows required")
    vectors = np.column_stack([np.ones(s.size), p])
    base = value(s)
    vegas = []
    for d in vectors.T:
        up, down = s + bump * d, s - bump * d
        if np.all(up >= 0) and np.all(down >= 0):
            v = (value(up) - value(down)) / (2 * bump)
        elif np.all(up >= 0):
            v = (-3 * base + 4 * value(up) - value(s + 2 * bump * d)) / (2 * bump)
        elif np.all(down >= 0):
            v = (3 * base - 4 * value(down) + value(s - 2 * bump * d)) / (2 * bump)
        else:
            raise ValueError("direction has neither feasible sign at zero sigma boundary")
        vegas.append(v * 0.01)
    return dict(parallel_vega_per_point=vegas[0], pca_vega_per_point=np.array(vegas[1:]))


def outside_model_sensitivities(
    quotes,
    curve_times,
    zero_rates,
    a,
    vol_knots,
    sigmas,
    curve_directions,
    vol_directions,
    *,
    rate_bump=1e-4,
    vol_bump=0.001,
):
    """Curve delta/gamma and absolute-sigma vega with explicit external shocks.

    Cash delta is the central price change for rate_bump (default 1bp).
    Hessians are per rate squared; vegas per .01 absolute rate volatility.
    A one-factor model permits any number of external environment buckets.
    """
    z, s = np.asarray(zero_rates, dtype=float), np.asarray(sigmas, dtype=float)

    def price_zeros(rates):
        return gaussian_environment_price(quotes, curve_times, rates, a, vol_knots, s)

    def price_sigmas(vols):
        return gaussian_environment_price(quotes, curve_times, z, a, vol_knots, vols)

    curve = rate_hedge_report(
        price_zeros, z, z, lambda rates: rates, curve_directions, bump=rate_bump
    )
    p = np.asarray(vol_directions, dtype=float)
    all_directions = np.column_stack([np.ones(s.size), p])
    if np.all(s[:, None] - vol_bump * abs(all_directions) >= 0):
        vol = volatility_hedge_report(price_sigmas, s, p, bump=vol_bump)
    else:
        vol = _vol_hedges(price_sigmas, s, p, vol_bump)
    return dict(
        value=price_zeros(z),
        curve=curve,
        vol=vol,
        pricing_factors=1,
        curve_buckets=z.size,
        vol_buckets=s.size,
    )
