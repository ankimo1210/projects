"""Private Hull GE Ch18: futures cashflows, Black pricing and exercise."""

import math


def futures_exercise_cash(current, last_settlement, strike, *, quantity=1, multiplier=1, kind="call", premium=0):
    """Exercise then close at current F; all quotes share multiplier cash units.

    The settlement cash can be negative if the last settlement was OTM.
    Futures entry costs zero; an ordinary option premium is paid separately.
    Signed futures prices are allowed in this accounting, not in Black pricing.
    """
    if not all(math.isfinite(x) for x in (current, last_settlement, strike, quantity, multiplier, premium)) or min(quantity, premium) < 0 or multiplier <= 0 or kind not in ("call", "put"):
        raise ValueError("finite quotes, nonnegative quantity/premium and positive multiplier required")
    sign = 1 if kind == "call" else -1
    exercised = sign*(current-strike) > 0
    position = sign*quantity if exercised else 0
    settlement = position*(last_settlement-strike)*multiplier
    close_cash = position*(current-last_settlement)*multiplier
    premium_cash = quantity*multiplier*premium
    return {"position": position, "settlement": settlement, "close_cash": close_cash,
            "payoff": settlement+close_cash, "premium_cash": premium_cash,
            "profit": settlement+close_cash-premium_cash}


def fractional_quote(whole, ticks, denominator):
    """Nonnegative printed fractional quote, e.g. 96-09 in 32nds."""
    if not all(math.isfinite(x) and int(x) == x for x in (whole, ticks, denominator)) or whole < 0 or denominator <= 0 or not 0 <= ticks < denominator:
        raise ValueError("nonnegative whole and integer ticks within positive denominator required")
    return whole+ticks/denominator


def rate_from_futures_quote(quote):
    """100 minus the printed percentage quote, returned as a decimal rate."""
    if not math.isfinite(quote):
        raise ValueError("finite quote required")
    return (100-quote)/100


def black_details(forward, strike, rate, sigma, maturity):
    """Ordinary European premium with deterministic discount and lognormal F."""
    from ._index_currency import carry_option_details

    return carry_option_details(forward, strike, rate, rate, sigma, maturity)


def futures_at_option_expiry(terminal_spot, rate, yield_rate, option_maturity, futures_maturity):
    """Terminal futures/spot basis under deterministic continuous carry."""
    if not all(math.isfinite(x) for x in (terminal_spot, rate, yield_rate, option_maturity, futures_maturity)) or terminal_spot <= 0 or option_maturity < 0 or futures_maturity < option_maturity:
        raise ValueError("positive spot and futures maturity at or after option expiry required")
    return terminal_spot*math.exp((rate-yield_rate)*(futures_maturity-option_maturity))


def spot_futures_equivalence(spot, strike, rate, yield_rate, sigma, maturity, *, futures_maturity=None):
    """Hull 18.3 European equal-maturity comparison; deterministic carry only."""
    from ._index_currency import carry_option_details

    spot_values = carry_option_details(spot, strike, rate, yield_rate, sigma, maturity)
    if futures_maturity is None:
        futures_maturity = maturity
    if not math.isfinite(futures_maturity) or not math.isclose(futures_maturity, maturity, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("spot/futures payoff equivalence requires matching maturities")
    future_values = black_details(spot_values["forward"], strike, rate, sigma, maturity)
    return {"forward": spot_values["forward"],
            "spot_call": spot_values["call"], "spot_put": spot_values["put"],
            "futures_call": future_values["call"], "futures_put": future_values["put"]}


def futures_parity(forward, strike, rate, maturity, *, call=None, put=None):
    """European futures quote recovery and residual, Hull 18.1.

    The textbook cash replication simplifies futures to terminal settlement;
    this is not a daily variation-margin/reinvestment cash simulator.
    """
    from ._index_currency import carry_bounds

    difference = carry_bounds(forward, strike, rate, rate, maturity)["call_minus_put"]
    if call is None and put is None:
        raise ValueError("at least one option quote required")
    if any(not math.isfinite(x) or x < 0 for x in (call, put) if x is not None):
        raise ValueError("nonnegative finite option quotes required")
    if call is None:
        call = put+difference
    if put is None:
        put = call-difference
    if min(call, put) < -1e-12:
        raise ValueError("given quote implies a negative opposite option price")
    call, put = max(call, 0), max(put, 0)
    return {"call": call, "put": put, "call_minus_put": difference,
            "residual": call-put-difference}


def futures_american_difference_bounds(forward, strike, rate, maturity):
    """Hull 18.2 American C-P interval, assuming nonnegative interest."""
    from ._index_currency import carry_american_difference_bounds

    return carry_american_difference_bounds(forward, strike, rate, rate, maturity)


def futures_option_bounds(forward, strike, rate, maturity):
    """European discounted intrinsic vs American immediate intrinsic, 18.3/4."""
    from ._index_currency import carry_bounds

    return {**carry_bounds(forward, strike, rate, rate, maturity),
            "american_call_lower": max(forward-strike, 0),
            "american_put_lower": max(strike-forward, 0)}


def futures_risk_neutral_law(forward, sigma, maturity):
    """Lognormal dF=sigma*F*dW under the money-market numeraire (18.5).

    Forward prices generally use the maturity-bond numeraire instead.
    """
    from ._stochastic_foundations import gbm_log_law

    return gbm_log_law(forward, 0, sigma, maturity)


def futures_tree_transition(forward, rate, sigma, dt):
    """One-step conditional martingale and discounted settlement expectation."""
    from .trees import crr_params, risk_neutral_p

    futures_risk_neutral_law(forward, sigma, dt)
    if not math.isfinite(rate):
        raise ValueError("finite rate required")
    up, down = crr_params(sigma, dt)
    if sigma == 0 or dt == 0:
        return {"up": up, "down": down, "probability": None, "discounted_settlement_mean": 0.0}
    probability = risk_neutral_p(up, down, rate, dt, q=rate)
    expected_change = forward*(probability*up+(1-probability)*down-1)
    return {"up": up, "down": down, "probability": probability,
            "discounted_settlement_mean": math.exp(-rate*dt)*expected_change}


def futures_pde_residual(forward, rate, sigma, value, f_time, gamma):
    """Hull 18.6: calendar f_t + .5*sigma^2*F^2*f_FF - r*f."""
    from ._bsm_foundations import bsm_pde_residual

    return bsm_pde_residual(forward, rate, sigma, value, f_time, 0, gamma)


def black_from_discount(forward, strike, discount_factor, sigma, maturity):
    """Forward-price Black with an explicit maturity-bond discount.

    With stochastic rates this requires lognormal forward under the
    maturity-bond measure; replacing it with futures is not justified here.
    """
    if not math.isfinite(discount_factor) or discount_factor <= 0 or (maturity == 0 and not math.isclose(discount_factor, 1, abs_tol=1e-12, rel_tol=1e-12)):
        raise ValueError("positive maturity discount, equal to one at expiry, required")
    result = black_details(forward, strike, 0, sigma, maturity)
    return {**result, "call": result["call"]*discount_factor,
            "put": result["put"]*discount_factor, "discount": discount_factor,
            "prepaid_spot": forward*discount_factor}
