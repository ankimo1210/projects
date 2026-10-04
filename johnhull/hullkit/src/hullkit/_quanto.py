"""Private Hull §30.3 quantos. FX quote is Y currency units per 1 X."""

import math

import numpy as np

from ._forward_black import forward_black_price
from ._timing_adjustment import frozen_ratio_density
from .trees import crr_price


def _validate(stock_volatility, fx_volatility, correlation, expiry):
    if min(stock_volatility, fx_volatility, expiry) < 0 or abs(correlation) > 1:
        raise ValueError("nonnegative volatilities/time and correlation in [-1,1] required")


def quanto_forward(foreign_forward, stock_volatility, forward_fx_volatility, correlation, expiry):
    """Single-settlement mean: F_Y exp(rho*sigma_V*sigma_forwardFX*T).

    Forward FX and its correlation belong to the same settlement date. Spot
    FX vol is not substituted into this general single-payment contract.
    A fixed conversion multiplier, if present, is applied to the result.
    """
    _validate(stock_volatility, forward_fx_volatility, correlation, expiry)
    if foreign_forward <= 0:
        raise ValueError("positive foreign forward required")
    return foreign_forward * math.exp(
        correlation * stock_volatility * forward_fx_volatility * expiry
    )


def quanto_effective_yield(
    rate_x, rate_y, dividend_y, stock_volatility, spot_fx_volatility, correlation
):
    """Spot/money-market version for multiple exercise dates, Hull 30.7.

    Under X measure, stock drift is r_Y-q_Y+rho*sigma_stock*sigma_spotFX.
    Discount at r_X; q_effective = r_X minus this drift. Rates, dividend,
    vols and correlation are constant in this model.
    """
    _validate(stock_volatility, spot_fx_volatility, correlation, 0)
    return rate_x - rate_y + dividend_y - correlation * stock_volatility * spot_fx_volatility


def quanto_option_price(
    spot,
    strike,
    rate_x,
    rate_y,
    dividend_y,
    stock_volatility,
    spot_fx_volatility,
    correlation,
    expiry,
    kind="call",
    *,
    american=False,
    steps=100,
    method="black",
):
    """Option in X units with unit fixed FX conversion.

    European Black and CRR use the same constant-coefficient drift. American
    always uses the CRR exercise grid; its printed 100-step value is not the
    continuous-exercise convergence price. A zero-volatility tree maximizes
    discounted deterministic payoff over its supplied exercise grid.
    """
    _validate(stock_volatility, spot_fx_volatility, correlation, expiry)
    if (
        min(spot, strike) <= 0
        or steps < 1
        or kind not in ("call", "put")
        or method not in ("black", "tree")
    ):
        raise ValueError("positive spot/strike/steps and valid kind/method required")
    q = quanto_effective_yield(
        rate_x, rate_y, dividend_y, stock_volatility, spot_fx_volatility, correlation
    )
    sign = 1 if kind == "call" else -1
    if expiry == 0:
        return max(sign * (spot - strike), 0.0)
    if stock_volatility == 0 and (american or method == "tree"):
        times = np.linspace(0, expiry, steps + 1) if american else np.array([expiry])
        return float(
            np.max(
                np.exp(-rate_x * times)
                * np.maximum(sign * (spot * np.exp((rate_x - q) * times) - strike), 0)
            )
        )
    if american or method == "tree":
        return crr_price(
            spot, strike, rate_x, stock_volatility, expiry, steps, q=q, kind=kind, american=american
        )
    forward = spot * math.exp((rate_x - q) * expiry)
    return forward_black_price(
        math.exp(-rate_x * expiry), forward, strike, stock_volatility, expiry, kind
    )


def quanto_measure_density(fx_brownian_y, spot_fx_volatility, expiry):
    """Raw money-market dQ_X/dQ_Y, deterministic rates and FX quoted Y/X."""
    _validate(0, spot_fx_volatility, 0, expiry)
    return frozen_ratio_density(fx_brownian_y, spot_fx_volatility, expiry)


def inverse_fx_drifts(rate_y, rate_x, spot_fx_volatility):
    """Inverse-quote Ito drift before and after Y→X measure change.

    E^Y[1/S] differs from 1/E^Y[S]. E^X[1/S] has the foreign/domestic
    interest differential after the covariance correction (Siegel issue).
    """
    _validate(0, spot_fx_volatility, 0, 0)
    return {
        "inverse_old_measure": rate_x - rate_y + spot_fx_volatility**2,
        "inverse_new_measure": rate_x - rate_y,
    }
