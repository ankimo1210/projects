"""Private Hull GE Ch20: smile axes, surfaces, scenarios and implied distributions."""

import math

import numpy as np


def parity_iv_details(spot, strike, rate, yield_rate, maturity, call_price, *, put_price=None):
    """European IVs and quote parity residual; input prices are never rounded.

    The default put is derived from parity. A supplied rounded put is solved
    separately, retaining its residual and IV gap. Near deep-ITM intrinsic
    values floating-point quotes can lose time value, making IV unidentifiable.
    """
    from ._index_currency import carry_implied_vol

    call_iv = carry_implied_vol(call_price, spot, strike, rate, yield_rate, maturity)
    parity_put = max(
        math.fsum(
            (
                call_price,
                strike * math.exp(-rate * maturity),
                -spot * math.exp(-yield_rate * maturity),
            )
        ),
        0,
    )
    put = parity_put if put_price is None else put_price
    # An exact deterministic call plus derived parity put is the same sigma=0
    # model. Do not use a price tolerance that would erase positive OTM quotes.
    put_iv = (
        0.0
        if put_price is None and call_iv == 0
        else carry_implied_vol(put, spot, strike, rate, yield_rate, maturity, kind="put")
    )
    return {
        "parity_put": parity_put,
        "put_price": put,
        "call_iv": call_iv,
        "put_iv": put_iv,
        "parity_residual": put - parity_put,
        "iv_difference": call_iv - put_iv,
    }


def normal_exceedance(standard_deviations):
    """Table20.1's two-sided normal benchmark, as probability, not percent."""
    from scipy.special import erfc

    z = np.asarray(standard_deviations, dtype=float)
    if np.any(~np.isfinite(z)) or np.any(z < 0):
        raise ValueError("finite nonnegative SD thresholds required")
    return erfc(z / math.sqrt(2))


def mixture_lognormal_moments(spot, rate, yield_rate, maturity, weights, volatilities):
    """Synthetic Q components share E[S_T]=F; match the terminal variance.

    This is an illustrative terminal distribution, not a fitted dynamic model
    or a replication of historical FX returns. Matching terminal variance is
    different from averaging volatilities or averaging their variances.
    """
    weights = np.asarray(weights, dtype=float)
    vols = np.asarray(volatilities, dtype=float)
    if (
        not all(math.isfinite(x) for x in (spot, rate, yield_rate, maturity))
        or spot <= 0
        or maturity <= 0
    ):
        raise ValueError("positive spot/time and finite rates required")
    if (
        weights.ndim != 1
        or weights.size == 0
        or weights.shape != vols.shape
        or np.any(~np.isfinite(weights))
        or np.any(~np.isfinite(vols))
        or np.any(weights < 0)
        or np.any(vols < 0)
        or not math.isclose(float(weights.sum()), 1, rel_tol=0, abs_tol=1e-12)
    ):
        raise ValueError("matching nonnegative weights/IV with probability sum one required")
    weights = weights / weights.sum()
    forward = spot * math.exp((rate - yield_rate) * maturity)
    relative_variance = float(weights @ np.expm1(vols**2 * maturity))
    matched = math.sqrt(math.log1p(relative_variance) / maturity)
    return {
        "mean": forward,
        "variance": forward**2 * relative_variance,
        "matched_volatility": matched,
        "weights": weights,
        "volatilities": vols,
    }


def mixture_lognormal_option(
    spot, strike, rate, yield_rate, maturity, weights, volatilities, *, kind="call"
):
    """Weighted European component prices, IV and moment-matched comparison."""
    from ._index_currency import carry_implied_vol, carry_option_details

    if strike <= 0 or kind not in ("call", "put"):
        raise ValueError("positive strike and call/put required to identify IV")
    moments = mixture_lognormal_moments(spot, rate, yield_rate, maturity, weights, volatilities)
    price = sum(
        float(w) * carry_option_details(spot, strike, rate, yield_rate, float(vol), maturity)[kind]
        for w, vol in zip(moments["weights"], moments["volatilities"], strict=True)
    )
    benchmark = carry_option_details(
        spot, strike, rate, yield_rate, moments["matched_volatility"], maturity
    )[kind]
    return {
        **moments,
        "price": price,
        "matched_price": benchmark,
        "implied_volatility": carry_implied_vol(
            price, spot, strike, rate, yield_rate, maturity, kind=kind
        ),
    }
