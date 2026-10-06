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


def _market_forward(spot, rate, yield_rate, maturity):
    if (
        not all(math.isfinite(x) for x in (spot, rate, yield_rate, maturity))
        or spot <= 0
        or maturity < 0
    ):
        raise ValueError("positive spot, nonnegative time and finite rates required")
    return spot * math.exp((rate - yield_rate) * maturity)


def smile_coordinates(strikes, spot, rate, yield_rate, volatilities, maturity, *, kind="call"):
    """Same smile on K, K/S, K/F and unadjusted spot-delta axes."""
    from .volatility import delta_from_strike

    forward = _market_forward(spot, rate, yield_rate, maturity)
    strikes = np.asarray(strikes, dtype=float)
    vols = np.asarray(volatilities, dtype=float)
    if (
        maturity <= 0
        or np.any(~np.isfinite(strikes))
        or np.any(strikes <= 0)
        or np.any(~np.isfinite(vols))
        or np.any(vols <= 0)
    ):
        raise ValueError("positive strikes/IV/time required for the smooth delta axis")
    delta = delta_from_strike(strikes, spot, rate, vols, maturity, q=yield_rate, kind=kind)
    return {
        "strike": strikes,
        "spot_moneyness": strikes / spot,
        "forward_moneyness": strikes / forward,
        "spot_delta": delta,
        "delta_convention": "spot, not premium-adjusted",
    }


def strike_from_smile_axis(
    axis, coordinate, spot, rate, yield_rate, sigma, maturity, *, kind="call"
):
    """Invert one coordinate at its supplied IV; this does not solve a smile fixed point."""
    from .volatility import strike_from_delta

    forward = _market_forward(spot, rate, yield_rate, maturity)
    values = np.asarray(coordinate, dtype=float)
    if axis == "scaled_log_forward_moneyness":
        if maturity <= 0 or np.any(~np.isfinite(values)):
            raise ValueError("finite scaled log coordinates and positive time required")
        return forward * np.exp(values * math.sqrt(maturity))
    if axis == "spot_delta":
        return strike_from_delta(values, spot, rate, sigma, maturity, q=yield_rate, kind=kind)
    if np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("positive finite strike/moneyness coordinates required")
    if axis == "strike":
        return values
    if axis == "spot_moneyness":
        return values * spot
    if axis == "forward_moneyness":
        return values * forward
    raise ValueError("axis must be strike, spot_moneyness, forward_moneyness or spot_delta")


def atm_definitions(spot, rate, yield_rate, sigma, maturity):
    """ATM spot, ATM forward and call/put 50 spot-delta strikes, when attainable."""
    return {
        "spot_strike": spot,
        "forward_strike": _market_forward(spot, rate, yield_rate, maturity),
        "call_50_delta_strike": float(
            strike_from_smile_axis("spot_delta", 0.5, spot, rate, yield_rate, sigma, maturity)
        ),
        "put_50_delta_strike": float(
            strike_from_smile_axis(
                "spot_delta", -0.5, spot, rate, yield_rate, sigma, maturity, kind="put"
            )
        ),
    }


def scaled_log_forward_moneyness(strikes, spot, rate, yield_rate, maturity):
    """Hull 20.5's ln(K/F)/sqrt(T), not standardized by an implied volatility."""
    forward = _market_forward(spot, rate, yield_rate, maturity)
    strikes = np.asarray(strikes, dtype=float)
    if maturity <= 0 or np.any(~np.isfinite(strikes)) or np.any(strikes <= 0):
        raise ValueError("positive strikes/time required for scaled log moneyness")
    return np.log(strikes / forward) / math.sqrt(maturity)


def interpolate_iv(maturities, moneyness, volatilities, time, relative_strike):
    """Table20.2 bilinear IV (decimal scale), rows T in years, columns K/S.

    Supports broadcast query arrays; outside-grid queries raise. There is no
    extrapolation, total-variance substitution or arbitrage repair. Convexity
    in call prices and calendar consistency must be checked separately.
    """
    t = np.asarray(maturities, dtype=float)
    m = np.asarray(moneyness, dtype=float)
    vol = np.asarray(volatilities, dtype=float)
    if t.ndim != 1 or m.ndim != 1 or min(t.size, m.size) < 2 or vol.shape != (t.size, m.size):
        raise ValueError("two increasing axes and a matching rectangular IV grid required")
    if (
        any(np.any(~np.isfinite(x)) for x in (t, m, vol))
        or np.any(t <= 0)
        or np.any(m <= 0)
        or np.any(vol < 0)
        or np.any(np.diff(t) <= 0)
        or np.any(np.diff(m) <= 0)
    ):
        raise ValueError("positive increasing time/moneyness and nonnegative finite IV required")
    qt, qm = np.broadcast_arrays(
        np.asarray(time, dtype=float), np.asarray(relative_strike, dtype=float)
    )
    if (
        np.any(~np.isfinite(qt))
        or np.any(~np.isfinite(qm))
        or np.any(qt < t[0])
        or np.any(qt > t[-1])
        or np.any(qm < m[0])
        or np.any(qm > m[-1])
    ):
        raise ValueError("query outside IV grid; no extrapolation is performed")
    i = np.clip(np.searchsorted(t, qt, side="right") - 1, 0, t.size - 2)
    j = np.clip(np.searchsorted(m, qm, side="right") - 1, 0, m.size - 2)
    tw = (qt - t[i]) / (t[i + 1] - t[i])
    mw = (qm - m[j]) / (m[j + 1] - m[j])
    value = (1 - tw) * ((1 - mw) * vol[i, j] + mw * vol[i, j + 1]) + tw * (
        (1 - mw) * vol[i + 1, j] + mw * vol[i + 1, j + 1]
    )
    return float(value) if value.ndim == 0 else value


def minimum_variance_delta(
    spot, strike, rate, yield_rate, sigma, maturity, iv_response, *, kind="call"
):
    """Hull 20.6 local delta: BSM delta + vega * dE[IV]/dS.

    IV and its conditional response use decimal volatility; vega is per 1.0
    volatility and the response is per spot-price unit. The response describes
    time-series co-movement, not the cross-sectional smile slope dIV/dK.
    This first-order hedge does not claim an exact finite-move variance minimum.
    """
    from .bsm import call_delta, put_delta, vega

    if (
        not all(
            math.isfinite(x) for x in (spot, strike, rate, yield_rate, sigma, maturity, iv_response)
        )
        or min(spot, strike, sigma, maturity) <= 0
        or kind not in {"call", "put"}
    ):
        raise ValueError("positive spot/strike/vol/time, finite IV response and call/put required")
    delta_fn = call_delta if kind == "call" else put_delta
    delta = float(delta_fn(spot, strike, rate, sigma, maturity, q=yield_rate))
    vol_sensitivity = float(vega(spot, strike, rate, sigma, maturity, q=yield_rate))
    correction = vol_sensitivity * iv_response
    return {
        "bsm_delta": delta,
        "vega": vol_sensitivity,
        "iv_response": iv_response,
        "vega_correction": correction,
        "minimum_variance_delta": delta + correction,
    }


def single_jump_details(spot, down_price, up_price, rate, maturity, strikes, *, yield_rate=0):
    """Hull 20.8 two terminal states: exact Q prices and a common European IV.

    Prices retain full precision. Inversion uses the OTM member of each parity
    pair, so zero-payoff endpoints yield IV=0 without subtracting intrinsic
    value. Printed rounded quotes must be inverted separately. This is a
    one-event terminal model, not a continuous-time jump process.
    """
    from ._index_currency import carry_implied_vol

    forward = _market_forward(spot, rate, yield_rate, maturity)
    strikes = np.asarray(strikes, dtype=float)
    if (
        not all(math.isfinite(x) for x in (down_price, up_price))
        or maturity <= 0
        or down_price <= 0
        or not down_price < forward < up_price
        or np.any(~np.isfinite(strikes))
        or np.any(strikes <= 0)
    ):
        raise ValueError(
            "positive time/strikes and terminal states bracketing the forward required"
        )
    probability = (forward - down_price) / (up_price - down_price)
    discount = math.exp(-rate * maturity)
    calls = discount * (
        probability * np.maximum(up_price - strikes, 0)
        + (1 - probability) * np.maximum(down_price - strikes, 0)
    )
    puts = discount * (
        probability * np.maximum(strikes - up_price, 0)
        + (1 - probability) * np.maximum(strikes - down_price, 0)
    )
    iv = np.empty_like(strikes)
    for index in np.ndindex(strikes.shape):
        strike = float(strikes[index])
        kind = "put" if strike < forward else "call"
        price = float(puts[index] if kind == "put" else calls[index])
        iv[index] = carry_implied_vol(price, spot, strike, rate, yield_rate, maturity, kind=kind)
    return {
        "up_factor": up_price / spot,
        "down_factor": down_price / spot,
        "growth_factor": forward / spot,
        "up_probability": probability,
        "call_prices": calls,
        "put_prices": puts,
        "implied_volatility": iv,
    }
