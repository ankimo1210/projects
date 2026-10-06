"""Private Ch36 project cashflows, risk adjustment and investment exercise states."""

import math

import numpy as np


def real_project_npv(initial, times, expected_cashflows, required_rate):
    """P expected incremental cash discounted at its stated continuous required return."""
    from .rates import bond_price

    if initial < 0:
        raise ValueError("nonnegative initial investment required")
    return float(bond_price(times, expected_cashflows, required_rate) - initial)


def two_state_required_returns(spot, up, down, strike, rate, physical_growth, maturity):
    """Two-state replicated call/put prices and their implied P continuous required returns.

    Stock P expected growth determines P probabilities. Q probabilities price the
    payoff; its own required return is inferred from that price, not imposed as r.
    A zero-price/zero-expectation payoff has no identifiable required return.
    """
    if (
        not np.isfinite([spot, up, down, strike, rate, physical_growth, maturity]).all()
        or min(spot, strike, down) < 0
        or up <= down
        or maturity <= 0
    ):
        raise ValueError("ordered nonnegative prices, positive time and finite rates required")
    q = (spot * math.exp(rate * maturity) - down) / (up - down)
    p = (spot * math.exp(physical_growth * maturity) - down) / (up - down)
    if not 0 <= q <= 1 or not 0 <= p <= 1:
        raise ValueError("P and Q means must lie within the supplied two states")
    result = {"p_physical": p, "p_risk_neutral": q}
    for kind in ["call", "put"]:
        cash = (
            np.maximum(np.array([up, down]) - strike, 0)
            if kind == "call"
            else np.maximum(strike - np.array([up, down]), 0)
        )
        price = float(math.exp(-rate * maturity) * np.dot([q, 1 - q], cash))
        expected = float(np.dot([p, 1 - p], cash))
        delta = float((cash[0] - cash[1]) / (up - down))
        result[kind] = {
            "price": price,
            "expected_payoff": expected,
            "required_return": math.log(expected / price) / maturity
            if min(expected, price) > 0
            else None,
            "delta": delta,
            "cash_bond": math.exp(-rate * maturity) * (cash[1] - delta * down),
        }
    return result


def risk_adjusted_drift(physical_drift, factor_loadings, risk_prices):
    """P drift minus L*lambda in a common independent-Brownian factor coordinate system."""
    mu = np.atleast_1d(np.asarray(physical_drift, dtype=float))
    L = np.asarray(factor_loadings, dtype=float)
    lam = np.atleast_1d(np.asarray(risk_prices, dtype=float))
    if (
        mu.ndim != 1
        or lam.ndim != 1
        or L.shape != (len(mu), len(lam))
        or not np.isfinite(mu).all()
        or not np.isfinite(L).all()
        or not np.isfinite(lam).all()
    ):
        raise ValueError("matching finite drifts/loadings/risk prices required")
    return mu - L @ lam


def rental_option(
    current_rent,
    physical_growth,
    volatility,
    market_price,
    rate,
    option_maturity,
    strike,
    area,
    lease_years,
):
    """Hull's option on a five-year-style level rent paid annually in advance.

    Annual rent is set on exercise, then held fixed through the lease. The annuity
    is valued at exercise and the option expectation is discounted once to today.
    The supplied market price of risk selects Q drift for a nontraded rent process.
    """
    from .bsm import call_price

    if (
        min(current_rent, strike) <= 0
        or min(volatility, option_maturity, area) < 0
        or lease_years < 1
        or int(lease_years) != lease_years
    ):
        raise ValueError("positive rent/strike/lease length and nonnegative vol/time/area required")
    growth = float(risk_adjusted_drift([physical_growth], [[volatility]], [market_price])[0])
    expected = current_rent * math.exp(growth * option_maturity)
    annuity = float(np.exp(-rate * np.arange(int(lease_years))).sum())
    payoff = float(area * annuity * call_price(expected, strike, 0, volatility, option_maturity))
    return {
        "annuity": annuity,
        "q_growth": growth,
        "expected_rent": expected,
        "expected_payoff": payoff,
        "value": payoff * math.exp(-rate * option_maturity),
    }


def capm_market_price(correlation, market_excess_return, market_volatility):
    """CAPM lambda=rho*market excess return/market volatility, in matching annual units."""
    if (
        not np.isfinite([correlation, market_excess_return, market_volatility]).all()
        or abs(correlation) > 1
        or market_volatility <= 0
    ):
        raise ValueError("valid correlation and positive market volatility required")
    return correlation * market_excess_return / market_volatility


def capm_risk_price_from_samples(
    variable_changes, market_returns, market_excess_return, *, periods_per_year=1
):
    """Estimate source correlation/annual volatility using synchronized supplied observations.

    Annual market premium is a separate caller input. This does not identify a
    proxy, establish causality or use the fitted sample as out-of-sample evidence.
    """
    x = np.asarray(variable_changes, dtype=float)
    m = np.asarray(market_returns, dtype=float)
    if (
        x.ndim != 1
        or x.shape != m.shape
        or len(x) < 2
        or not np.isfinite(x).all()
        or not np.isfinite(m).all()
        or periods_per_year <= 0
    ):
        raise ValueError("matching finite samples and positive annualization required")
    covariance = np.cov(x, m, ddof=1)
    if min(covariance[0, 0], covariance[1, 1]) <= 0:
        raise ValueError("positive sample variances required for correlation")
    rho = float(covariance[0, 1] / math.sqrt(covariance[0, 0] * covariance[1, 1]))
    vol = math.sqrt(covariance[1, 1] * periods_per_year)
    return {
        "correlation": rho,
        "market_volatility": vol,
        "lambda": capm_market_price(rho, market_excess_return, vol),
    }
