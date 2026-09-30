"""Simple stock-price cliquets with payments at every reset (Hull GE §26.6)."""

import numpy as np

from . import bsm
from .forward_start import forward_start_call


def _real(name, value):
    if np.iscomplexobj(value):
        raise ValueError(f"{name} must be real")
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be representable real numbers") from exc
    if np.any(~np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


def _price(kind, S, r, sigma, payment_times, q):
    end = _real("payment_times", payment_times)
    if end.ndim != 1 or not end.size or np.any(end <= 0) or np.any(np.diff(end) <= 0):
        raise ValueError("payment_times must be nonempty, one-dimensional, positive and increasing")
    s, rate, vol, yield_ = np.broadcast_arrays(
        *[
            _real(name, value)
            for name, value in zip(("S", "r", "sigma", "q"), (S, r, sigma, q), strict=True)
        ]
    )
    if np.any(s <= 0) or np.any(vol < 0):
        raise ValueError("require S > 0 and sigma >= 0")
    start = np.r_[0.0, end[:-1]]
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            if kind == "call":
                legs = forward_start_call(
                    s[..., None], rate[..., None], vol[..., None], start, end, yield_[..., None]
                )
            else:
                unit = bsm.put_price(
                    1.0, 1.0, rate[..., None], vol[..., None], end - start, yield_[..., None]
                )
                legs = s[..., None] * np.exp(-yield_[..., None] * start) * unit
            result = np.sum(legs, axis=-1)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("cliquet price is outside the representable range") from exc
    if np.any(~np.isfinite(result)):
        raise ValueError("cliquet price is outside the representable range")
    return result.item() if result.ndim == 0 else result


def cliquet_call(S, r, sigma, payment_times, q=0.0):
    """Value a series of ATM calls, paying max(S(t_i)-S(t_{i-1}),0) at t_i.

    t_0=0; the first strike is today's S and later strikes are reset to the
    preceding fixing's stock price. Payoffs are currency per one underlying,
    not fixed-notional returns. Constant GBM parameters: continuously
    compounded annual r/q, annual sigma, times in years. Each payment is
    discounted from its own date. No global/local caps, floors or termination.

    Market inputs broadcast; payment_times is a shared nonempty 1D schedule
    with strictly positive increasing finite dates. Require finite real
    inputs, S>0 and sigma>=0. Zero volatility uses the deterministic limit.
    Return float for scalar markets, otherwise ndarray. Invalid inputs and
    unrepresentable calculations raise ValueError.
    """
    return _price("call", S, r, sigma, payment_times, q)


def cliquet_put(S, r, sigma, payment_times, q=0.0):
    """Value max(S(t_{i-1})-S(t_i),0) paid at each t_i.

    Uses the same units, reset/payment rules, GBM assumptions, broadcasting,
    validation and exclusions as cliquet_call. Each leg is an ATM put at its
    random reset strike, not a put at the initial spot.
    """
    return _price("put", S, r, sigma, payment_times, q)
