"""Simple European chooser replication (Hull 11e GE §26.8, pp.619–620)."""

import numpy as np

from . import bsm


def chooser_price(S, K, r, sigma, T1, T2, q=0.0):
    """Value choosing at T1 a European call or put with common K and expiry T2.

    Under constant-rate/yield/volatility GBM, the package is one T2 call and
    exp(-q*(T2-T1)) T1 puts struck at K*exp(-(r-q)*(T2-T1)). T1 is the
    decision time; the selected option's payoff settles at T2.

    All finite real market inputs broadcast. S,K > 0, sigma >= 0 and
    0 <= T1 <= T2. Returns float for a scalar market, otherwise ndarray.
    Invalid inputs or unrepresentable intermediate/results raise ValueError.
    T1=0 chooses today's larger vanilla value; T1=T2 is a straddle;
    zero volatility is the deterministic larger vanilla value.
    """
    arrays = []
    for value in (S, K, r, sigma, T1, T2, q):
        try:
            array = np.asarray(value)
            if np.iscomplexobj(array) or (
                array.dtype.kind == "O" and any(np.iscomplexobj(item) for item in array.flat)
            ):
                raise ValueError("chooser inputs must be real")
            array = np.asarray(array, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("chooser inputs must be finite real values") from exc
        if np.any(~np.isfinite(array)):
            raise ValueError("chooser inputs must be finite real values")
        arrays.append(array)
    shape = np.broadcast_shapes(*(a.shape for a in arrays))
    s, k, rate, vol, t1, t2, yield_ = (a.ravel() for a in np.broadcast_arrays(*arrays))
    if np.any((s <= 0) | (k <= 0) | (vol < 0) | (t1 < 0) | (t1 > t2)):
        raise ValueError("require S,K>0, sigma>=0 and 0<=T1<=T2")
    if not s.size:
        return np.empty(shape)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            call = np.maximum(bsm.call_price(s, k, rate, vol, t2, yield_), 0.0)
            out = call.copy()
            immediate = (t1 == 0) | (vol == 0)
            terminal = (~immediate) & (t1 == t2)
            boundary = immediate | terminal
            if np.any(boundary):
                put = np.maximum(
                    bsm.put_price(
                        s[boundary],
                        k[boundary],
                        rate[boundary],
                        vol[boundary],
                        t2[boundary],
                        yield_[boundary],
                    ),
                    0.0,
                )
                out[boundary] = np.where(
                    immediate[boundary], np.maximum(call[boundary], put), call[boundary] + put
                )
            active = ~boundary
            if np.any(active):
                tau = t2[active] - t1[active]
                strike = k[active] * np.exp(-(rate[active] - yield_[active]) * tau)
                weight = np.exp(-yield_[active] * tau)
                # A strike that underflows to zero has a zero put value.
                positive = (strike > 0) & (weight > 0)
                extra = np.zeros(tau.shape)
                if np.any(positive):
                    indices = np.flatnonzero(active)[positive]
                    extra[positive] = weight[positive] * np.maximum(
                        bsm.put_price(
                            s[indices],
                            strike[positive],
                            rate[indices],
                            vol[indices],
                            t1[indices],
                            yield_[indices],
                        ),
                        0.0,
                    )
                out[active] += extra
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("chooser calculation is not representable") from exc
    if not np.all(np.isfinite(out)):
        raise ValueError("chooser calculation is not representable")
    return float(out[0]) if shape == () else out.reshape(shape)
