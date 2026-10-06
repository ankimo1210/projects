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


def operating_cashflows(tree, annual_units, variable_cost, fixed_cost):
    """Interval-end operating cash, using annual output/fixed cost times tree dt.

    Root cash is zero. At later nodes revenue uses that interval's endpoint spot;
    values computed below are AFTER that cash has been paid. Units and monetary
    scale are caller supplied; expansion need not scale fixed costs proportionally.
    """
    if annual_units < 0 or not np.isfinite([annual_units, variable_cost, fixed_cost]).all():
        raise ValueError("nonnegative output and finite costs required")
    return [np.zeros_like(tree["levels"][0]["spot"])] + [
        (annual_units * (level["spot"] - variable_cost) - fixed_cost) * tree["dt"]
        for level in tree["levels"][1:]
    ]


def _project_cashflows(tree, cashflows):
    if len(cashflows) != len(tree["levels"]):
        raise ValueError("one cashflow vector per tree layer required")
    arrays = [np.asarray(x, dtype=float) for x in cashflows]
    if any(
        x.shape != level["spot"].shape or not np.isfinite(x).all()
        for x, level in zip(arrays, tree["levels"], strict=True)
    ):
        raise ValueError("finite cashflow vectors matching tree nodes required")
    return arrays


def project_value_tree(tree, cashflows, rate):
    """Q PV of subsequent operating cash, after current-node payment; no terminal value.

    Supply all layer vectors including root (already paid, hence not counted).
    Initial investment is separate and is not subtracted from operating project PV.
    """
    cash = _project_cashflows(tree, cashflows)
    if not np.isfinite(rate):
        raise ValueError("finite discount rate required")
    values = [np.zeros_like(x) for x in cash]
    discount = math.exp(-rate * tree["dt"])
    for t in range(len(values) - 2, -1, -1):
        level = tree["levels"][t]
        future = cash[t + 1] + values[t + 1]
        values[t] = discount * np.sum(level["probabilities"] * future[level["successors"]], axis=1)
    return values


def investment_options(
    tree,
    cashflows,
    rate,
    *,
    allow_abandon=False,
    salvage=0,
    expanded_cashflows=None,
    expansion_cost=None,
):
    """Irreversible expansion/abandonment, with four exercise states per node.

    States: alive/unexpanded, alive/expanded, abandoned/unexpanded, abandoned/expanded.
    Decisions occur after current cash, so only later cash changes on exercise.
    Expansion is paid immediately once; abandoned states are absorbing and have no
    future operating cash. Salvage is the same net exit receipt in both live states,
    including at horizon end; it may be negative. Expanded cash vectors explicitly
    specify costs/revenues, avoiding an assumed proportional expansion. All values
    exclude initial investment, which is subtracted once outside this function.
    """
    base = _project_cashflows(tree, cashflows)
    if (expanded_cashflows is None) != (expansion_cost is None):
        raise ValueError("expanded cashflows and expansion cost must be supplied together")
    can_expand = expanded_cashflows is not None
    enlarged = _project_cashflows(tree, expanded_cashflows) if can_expand else base
    if not np.isfinite([rate, salvage]).all() or (
        can_expand and (not np.isfinite(expansion_cost) or expansion_cost < 0)
    ):
        raise ValueError("finite rate/salvage and nonnegative finite expansion cost required")
    values = [np.zeros((4, len(x))) for x in base]
    decisions = [np.full(x.shape, "continue", dtype="<U10") for x in values]
    for decision in decisions:
        decision[2:] = "absorbed"
    decisions[-1][:2] = "complete"
    if allow_abandon and salvage > 0:
        values[-1][:2] = salvage
        decisions[-1][:2] = "abandon"
    discount = math.exp(-rate * tree["dt"])
    for t in range(len(base) - 2, -1, -1):
        level = tree["levels"][t]
        for state, cash in [(1, enlarged), (0, base)]:
            future = cash[t + 1] + values[t + 1][state]
            continuation = discount * np.sum(
                level["probabilities"] * future[level["successors"]], axis=1
            )
            values[t][state] = continuation
            if allow_abandon:
                exercise = salvage > values[t][state]
                values[t][state, exercise] = salvage
                decisions[t][state, exercise] = "abandon"
            if state == 0 and can_expand:
                expanded = values[t][1] - expansion_cost
                exercise = expanded > values[t][0]
                values[t][0, exercise] = expanded[exercise]
                decisions[t][0, exercise] = "expand"
    base_values = project_value_tree(tree, base, rate)
    return {
        "value": float(values[0][0, 0]),
        "state_values": values,
        "decisions": decisions,
        "base_values": base_values,
        "option_values": [
            states[0] - plain for states, plain in zip(values, base_values, strict=True)
        ],
    }
