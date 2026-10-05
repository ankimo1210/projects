"""Private Hull GE Ch11 calculations; educational conventions are explicit."""

import math

import numpy as np

from . import bsm


def _market(spot, strike, rate, volatility, maturity):
    values = np.asarray([spot, strike, rate, volatility, maturity], dtype=float)
    if not np.all(np.isfinite(values)) or min(spot, strike, volatility, maturity) < 0:
        raise ValueError("finite inputs and nonnegative spot, strike, volatility, maturity required")


def _european_pair(spot, strike, rate, volatility, maturity, times=(), amounts=()):
    """Escrowed-dividend BSM: volatility applies to spot less dividend PV.

    Ex-dates <= maturity are paid before terminal exercise; dates stay fixed
    when maturity changes. This model convention is not a general stock-jump model.
    Zero spot/strike endpoints are analytic limits, avoiding undefined log(S/K).
    """
    _market(spot, strike, rate, volatility, maturity)
    prepaid = spot - bsm.pv_dividends(times, amounts, rate, maturity)
    if prepaid < 0:
        raise ValueError("dividend PV cannot exceed spot in the escrowed model")
    if prepaid == 0 or strike == 0:
        difference = prepaid - strike * math.exp(-rate * maturity)
        return max(difference, 0), max(-difference, 0)
    return (float(bsm.call_price(prepaid, strike, rate, volatility, maturity)),
            float(bsm.put_price(prepaid, strike, rate, volatility, maturity)))


def factor_prices(values, *, factor, spot=50, strike=50, rate=.05, volatility=.3,
                  maturity=1, dividend_times=(), dividend_amounts=()):
    """European call/put curves for Hull Figures 11.1/11.2 and Table 11.1.

    ``dividend_scale`` multiplies the caller's cash amounts at unchanged dates.
    Values may include zero price/strike/maturity/volatility endpoints.
    """
    baseline = dict(spot=spot, strike=strike, rate=rate, volatility=volatility, maturity=maturity)
    if factor not in (*baseline, "dividend_scale"):
        raise ValueError("unknown option price factor")
    axis = np.asarray(values, dtype=float)
    if axis.ndim != 1 or not np.all(np.isfinite(axis)):
        raise ValueError("values must be a finite one-dimensional curve axis")
    call, put = [], []
    for value in axis:
        inputs = baseline.copy()
        amounts = dividend_amounts
        if factor == "dividend_scale":
            if value < 0:
                raise ValueError("dividend scale must be nonnegative")
            amounts = np.asarray(dividend_amounts, dtype=float) * value
        else:
            inputs[factor] = float(value)
        c, p = _european_pair(**inputs, times=dividend_times, amounts=amounts)
        call.append(c)
        put.append(p)
    return dict(values=axis.copy(), call=np.asarray(call), put=np.asarray(put))
