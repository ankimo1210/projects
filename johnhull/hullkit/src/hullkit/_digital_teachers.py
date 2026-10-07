"""Private RB-F05 cash-or-nothing GBM teachers (payout 1, no dividends).

Prices are currency/payout units, deltas currency per spot unit. IID normal
draws are supplied by the caller; the last axis is the independent path axis.
Conditioning integrates out a GBM increment exactly. The ramp changes the
contract and must not be called an unbiased digital teacher.
"""

import numpy as np
from scipy.special import ndtr


def _inputs(spot, strike, rate, volatility, maturity):
    values = np.broadcast_arrays(
        *[np.asarray(v, dtype=float) for v in (spot, strike, rate, volatility, maturity)]
    )
    if any(not np.all(np.isfinite(v)) for v in values):
        raise ValueError("parameters must be finite")
    if any(np.any(values[i] <= 0) for i in (0, 1, 3, 4)):
        raise ValueError("spot, strike, volatility and maturity must be positive")
    return values


def _phi(z):
    return np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)


def analytic(spot, strike, rate, volatility, maturity):
    """Return exact digital price and spot delta under dividend-free GBM."""
    s, k, r, v, t = _inputs(spot, strike, rate, volatility, maturity)
    d2 = (np.log(s / k) + (r - v * v / 2) * t) / (v * np.sqrt(t))
    discount = np.exp(-r * t)
    return discount * ndtr(d2), discount * _phi(d2) / (s * v * np.sqrt(t))


def samples(
    spot,
    strike,
    rate,
    volatility,
    maturity,
    z,
    *,
    conditioning_fraction=0.5,
    bump=0.1,
    ramp_width=2.0,
):
    """Return payoff, LRM, zero-pathwise, CRN, exact-conditioned and ramp samples.

    Conditioning observes GBM at fraction alpha of T and integrates out the
    remaining (1-alpha)T. Alpha=0 gives the deterministic exact price/delta.
    Bump and ramp widths are in spot units. A CRN central difference estimates
    the *finite-bump* derivative; it is not an exactly unbiased delta estimator.
    """
    values = _inputs(spot, strike, rate, volatility, maturity)
    if not 0 <= conditioning_fraction < 1:
        raise ValueError("conditioning fraction must be in [0,1)")
    if not 0 < bump < np.min(values[0]) or not 0 < ramp_width < np.min(values[1]):
        raise ValueError("positive bump < spot and positive ramp width < strike required")
    z = np.asarray(z, dtype=float)
    if z.ndim == 0 or not np.all(np.isfinite(z)):
        raise ValueError("finite path draws required")
    s, k, r, v, t = [value[..., None] for value in values]
    root_t = np.sqrt(t)
    multiplier = np.exp((r - v * v / 2) * t + v * root_t * z)
    terminal = s * multiplier
    discount = np.exp(-r * t)
    payoff = discount * (terminal > k)
    tau = (1 - conditioning_fraction) * t
    log_mid = np.log(s / k) + (r - v * v / 2) * conditioning_fraction * t
    log_mid = log_mid + v * np.sqrt(conditioning_fraction * t) * z
    d = (log_mid + (r - v * v / 2) * tau) / (v * np.sqrt(tau))
    return {
        "payoff": payoff,
        "lrm": payoff * z / (s * v * root_t),
        "pathwise": np.zeros_like(payoff),
        "conditional_price": discount * ndtr(d),
        "conditional_delta": discount * _phi(d) / (s * v * np.sqrt(tau)),
        "crn_bump": discount
        * (((s + bump) * multiplier > k).astype(float) - ((s - bump) * multiplier > k))
        / (2 * bump),
        "ramp_price": discount * np.clip((terminal - k + ramp_width) / (2 * ramp_width), 0, 1),
        "ramp_delta": discount
        * terminal
        / (2 * ramp_width * s)
        * ((terminal > k - ramp_width) & (terminal < k + ramp_width)),
    }


def summarize(values):
    """Return IID sample mean and standard error over the last (path) axis."""
    values = np.asarray(values, dtype=float)
    if values.ndim == 0 or values.shape[-1] < 2:
        raise ValueError("at least two IID samples are needed for a standard error")
    return values.mean(axis=-1), values.std(axis=-1, ddof=1) / np.sqrt(values.shape[-1])


def lrm_variance(spot, strike, rate, volatility, maturity):
    """Return exact per-path LRM delta variance (squared currency/spot units)."""
    s, k, r, v, t = _inputs(spot, strike, rate, volatility, maturity)
    a = (np.log(k / s) - (r - v * v / 2) * t) / (v * np.sqrt(t))
    return (
        np.exp(-2 * r * t)
        * np.maximum(a * _phi(a) + ndtr(-a) - _phi(a) ** 2, 0)
        / (s * s * v * v * t)
    )
