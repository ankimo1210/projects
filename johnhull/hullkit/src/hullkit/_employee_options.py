"""Private Hull GE Ch16: equity awards and employee-option stopping rules."""

import math

import numpy as np

from . import bsm, trees
from ._option_mechanics import option_cashflows


def equity_award_payoffs(terminal_stock, grant_spot, grant_strike, terminal_index, grant_index):
    """One RSU/MSU and an index-linked option, without caps or averaging."""
    if not all(math.isfinite(x) for x in (terminal_stock, grant_spot, grant_strike, terminal_index, grant_index)) or min(terminal_stock, grant_strike, terminal_index) < 0 or min(grant_spot, grant_index) <= 0:
        raise ValueError("positive grant stock/index and nonnegative terminal values/strike required")
    indexed_strike = grant_strike*terminal_index/grant_index
    shares = terminal_stock/grant_spot
    return {"rsu_value": terminal_stock, "msu_shares": shares, "msu_value": shares*terminal_stock, "indexed_strike": indexed_strike, "indexed_option_payoff": max(terminal_stock-indexed_strike, 0)}


def expected_life_bsm(spot, strike, rate, sigma, expected_life, *, dividend_pv=0, quantity=1):
    """Ex16.1 expected-life approximation, not an exact ESO valuation."""
    if not all(math.isfinite(x) for x in (rate, dividend_pv, quantity)) or min(dividend_pv, quantity) < 0:
        raise ValueError("finite rate and nonnegative dividend PV/quantity required")
    value = float(bsm.call_price(spot-dividend_pv, strike, rate, sigma, expected_life))
    return {"unit_value": value, "total_value": quantity*value}


def employee_option_tree(spot, strike, rate, sigma, maturity, steps, *, vesting=0,
                         departure_probability=0, exercise_probabilities=None,
                         exercise_multiple=None, optimal_exercise=False, dividend_yield=0):
    """CRR employee call with vesting, departures and one voluntary policy.

    Node (i,j) counts j down moves, with j=0 the highest stock, as in trees.py.
    Departure probability is per step, not per year. To reproduce Figure16.1
    it acts at each nonterminal node INCLUDING the root, after any voluntary
    decision; terminal payoffs have no extra departure factor. Departures
    forfeit unvested/OTM rights and immediately exercise vested ITM rights.

    The multiple policy triggers inclusively at S/K >= multiple. Callers must
    align the threshold with their CRR grid for the source's boundary advice;
    arbitrary grids introduce exercise-boundary discretization error. Infinite
    multiple means no voluntary exercise, not general optimal stopping.
    expected_life is the Q mean termination time, including forfeitures.
    """
    if not all(math.isfinite(x) for x in (spot, strike, rate, sigma, maturity, vesting, dividend_yield)) or spot <= 0 or strike < 0 or sigma < 0 or maturity <= 0 or not 0 <= vesting <= maturity or steps < 1 or int(steps) != steps:
        raise ValueError("valid stock/strike/volatility, positive tree life/steps and vesting in life required")
    steps = int(steps)
    leave = np.broadcast_to(np.asarray(departure_probability, dtype=float), (steps,))
    if not np.all(np.isfinite(leave)) or np.any((leave < 0) | (leave > 1)):
        raise ValueError("departure probabilities must be in [0,1]")
    probabilities = {} if exercise_probabilities is None else dict(exercise_probabilities)
    if (exercise_multiple is not None)+(exercise_probabilities is not None)+bool(optimal_exercise) > 1:
        raise ValueError("choose one voluntary exercise policy")
    if exercise_multiple is not None and (math.isnan(exercise_multiple) or exercise_multiple <= 0 or strike <= 0):
        raise ValueError("positive strike/multiple required (infinite multiple retains)")
    for (i, j), probability in probabilities.items():
        if not 0 <= i < steps or int(i) != i or not 0 <= j <= i or int(j) != j or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("nonterminal node and exercise probability in [0,1] required")
    dt = maturity/steps
    growth = math.exp((rate-dividend_yield)*dt)
    discount = math.exp(-rate*dt)
    if sigma == 0:
        up = down = growth
        p = .5
        stock = [np.full(i+1, spot*math.exp((rate-dividend_yield)*i*dt)) for i in range(steps+1)]
    else:
        up, down = trees.crr_params(sigma, dt)
        p = trees.risk_neutral_p(up, down, rate, dt, dividend_yield)
        log_up = sigma*math.sqrt(dt)
        stock = [spot*np.exp(log_up*(i-2*np.arange(i+1))) for i in range(steps+1)]
    values, continuation, exercise, survival, forfeiture, life = ([None]*(steps+1) for _ in range(6))
    values[-1] = np.maximum(stock[-1]-strike, 0)
    life[-1] = np.full(steps+1, maturity)
    for i in range(steps-1, -1, -1):
        time = i*dt
        continuation[i] = discount*(p*values[i+1][:-1]+(1-p)*values[i+1][1:])
        intrinsic = np.maximum(stock[i]-strike, 0)
        vested = time >= vesting or math.isclose(time, vesting, rel_tol=8*np.finfo(float).eps, abs_tol=0)
        eligible = vested & (intrinsic > 0)
        voluntary = np.array([probabilities.get((i, j), 0) for j in range(i+1)], dtype=float)
        if optimal_exercise:
            voluntary = (intrinsic > continuation[i]).astype(float)
        elif exercise_multiple is not None:
            boundary = strike*exercise_multiple
            voluntary = ((stock[i] >= boundary) | np.isclose(stock[i], boundary, rtol=8*np.finfo(float).eps, atol=0)).astype(float)
        voluntary = np.where(eligible, voluntary, 0)
        exercise[i] = np.where(eligible, voluntary+(1-voluntary)*leave[i], 0)
        survival[i] = (1-voluntary)*(1-leave[i])
        forfeiture[i] = np.maximum(1-exercise[i]-survival[i], 0)
        values[i] = exercise[i]*intrinsic+survival[i]*continuation[i]
        life[i] = (1-survival[i])*time+survival[i]*(p*life[i+1][:-1]+(1-p)*life[i+1][1:])
    return {"price": float(values[0][0]), "stock": stock, "option": values,
            "continuation": continuation, "exercise_probability": exercise,
            "survival_probability": survival, "forfeiture_probability": forfeiture,
            "expected_life": float(life[0][0]), "life_nodes": life,
            "up": up, "down": down, "growth": growth, "up_probability": p, "discount": discount, "dt": dt}


def exercise_multiple_estimate(stock_prices, strikes, event_types):
    """Unweighted mean S/K for voluntary exercise observations only.

    The caller classifies exercise events; departures and maturity settlements
    are excluded from the behavioural estimate, as in GE p.379.
    """
    stock = np.asarray(stock_prices, dtype=float)
    strikes = np.asarray(strikes, dtype=float)
    events = np.asarray(event_types)
    if stock.ndim != 1 or stock.shape != strikes.shape or stock.shape != events.shape or not np.all(np.isfinite(stock)) or not np.all(np.isfinite(strikes)) or np.any(stock <= 0) or np.any(strikes <= 0) or not np.all(np.isin(events, ["voluntary", "departure", "maturity"])):
        raise ValueError("matching positive prices/strikes and classified events required")
    keep = events == "voluntary"
    if not np.any(keep):
        raise ValueError("no voluntary exercise observations to estimate a multiple")
    return float(np.mean(stock[keep]/strikes[keep]))


def mirrored_exercise_cash(spot, strike, exercise_fraction, total_units):
    """Market-based security mirrors the observed fraction of ESO exercise."""
    if not all(math.isfinite(x) for x in (spot, strike, exercise_fraction, total_units)) or min(spot, strike, total_units) < 0 or not 0 <= exercise_fraction <= 1:
        raise ValueError("nonnegative stock/strike/units and fraction in [0,1] required")
    units = exercise_fraction*total_units
    cash = option_cashflows(spot, strike, 0, quantity=units)
    return {"per_option_payoff": float(cash["per_unit_payoff"]), "exercised_units": units, "cash_total": float(cash["payoff"])}
