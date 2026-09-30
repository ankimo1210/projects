"""ATM European forward-start calls under constant-parameter GBM (Hull §26.5)."""

import numpy as np

from . import bsm


def forward_start_call(S, r, sigma, T1, T2, q=0.0):
    """Value ``max(S(T2) - S(T1), 0)`` paid at ``T2``.

    ``T1`` is the strike-fixing/start time, ``T2`` is expiry, both in years
    from today. ``r`` and ``q`` are continuously compounded annual rates;
    ``sigma`` is annual volatility. Hull GE p.618 gives ``c * exp(-q*T1)``,
    where ``c`` is today's ATM call with life ``T2-T1``. The fixing-time
    strike is random; it is not today's spot.

    Inputs broadcast. Spot must be positive, volatility nonnegative, and
    ``0 <= T1 <= T2``; all inputs must be finite and real. Equal times give
    zero, zero volatility uses the deterministic limit. Return a float for
    scalar inputs, otherwise an ndarray. Invalid or unrepresentable inputs
    raise ValueError. Constant parameters and a continuous dividend yield
    are required; this is not an employee-option vesting/exercise model.
    """
    values = []
    for name, value in zip(
        ("S", "r", "sigma", "T1", "T2", "q"), (S, r, sigma, T1, T2, q), strict=True
    ):
        if np.iscomplexobj(value):
            raise ValueError(f"{name} must be real")
        array = np.asarray(value, dtype=float)
        if np.any(~np.isfinite(array)):
            raise ValueError(f"{name} must be finite")
        values.append(array)
    s, rate, vol, start, expiry, yield_ = np.broadcast_arrays(*values)
    if np.any(s <= 0) or np.any(vol < 0) or np.any(start < 0) or np.any(expiry < start):
        raise ValueError("require S > 0, sigma >= 0 and 0 <= T1 <= T2")
    result = np.zeros(s.shape, dtype=float)
    active = expiry > start
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            if np.any(active):
                tau = expiry[active] - start[active]
                unit = bsm.call_price(1.0, 1.0, rate[active], vol[active], tau, yield_[active])
                result[active] = s[active] * np.exp(-yield_[active] * start[active]) * unit
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("forward-start price is outside the representable range") from exc
    if np.any(~np.isfinite(result)):
        raise ValueError("forward-start price is outside the representable range")
    return result.item() if result.ndim == 0 else result
