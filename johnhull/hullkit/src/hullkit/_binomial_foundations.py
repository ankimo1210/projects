"""Private Hull GE Ch13: replication, direct state sums and measure changes."""

import math

import numpy as np
from scipy.stats import binom


def one_step_replication(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity):
    """Stock and signed present bank account replicating two terminal states.

    No dividends. A negative bank balance means borrowing. This is the GE
    4% example, with no actual-world probability needed for replication.
    """
    if not all(math.isfinite(v) for v in (spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity)) or spot <= 0 or down_stock < 0 or up_stock <= down_stock or maturity < 0:
        raise ValueError("finite inputs, positive spot and distinct ordered terminal states required")
    growth = math.exp(rate*maturity)
    probability = (spot*growth-down_stock)/(up_stock-down_stock)
    if not 0 < probability < 1:
        raise ValueError("no-arbitrage requires down stock < spot growth < up stock")
    delta = (up_payoff-down_payoff)/(up_stock-down_stock)
    terminal_bank = up_payoff-delta*up_stock
    bank = terminal_bank/growth
    return dict(delta=delta, bank=bank, terminal_bank=terminal_bank,
                price=delta*spot+bank, probability=probability)


def physical_comparison(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity, *, physical_drift):
    """Contrast actual-world expectation with the replicated, drift-free price.

    The option's inferred required return is defined only when both its price
    and actual-world payoff expectation are positive. It is not the stock's
    drift or a generally reusable discount rate for other payoffs.
    """
    if maturity <= 0 or not math.isfinite(physical_drift):
        raise ValueError("positive maturity and finite physical drift required")
    replica = one_step_replication(spot, up_stock, down_stock, up_payoff, down_payoff, rate, maturity)
    physical_probability = (spot*math.exp(physical_drift*maturity)-down_stock)/(up_stock-down_stock)
    if not 0 <= physical_probability <= 1:
        raise ValueError("physical drift must fit the two stock outcomes")
    expectation = physical_probability*up_payoff+(1-physical_probability)*down_payoff
    price = replica["price"]
    required = math.log(expectation/price)/maturity if expectation > 0 and price > 0 else None
    q_probability = replica["probability"]
    return dict(physical_probability=physical_probability,
                physical_payoff_expectation=expectation,
                required_discount_rate=required, risk_neutral_probability=q_probability,
                price=price, risk_free_discounted_physical_payoff=expectation*math.exp(-rate*maturity),
                q_stock_expectation=q_probability*up_stock+(1-q_probability)*down_stock,
                p_stock_expectation=physical_probability*up_stock+(1-physical_probability)*down_stock)


def _binomial_spec(spot, strike, rate, maturity, steps, up, down, q, kind, probability):
    if not all(math.isfinite(x) for x in (spot, strike, rate, maturity, up, down, q)) or spot <= 0 or strike < 0 or maturity <= 0 or steps < 1 or int(steps) != steps or not up > down > 0:
        raise ValueError("positive spot/time/steps, nonnegative strike and ordered positive moves required")
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    dt = maturity/steps
    p = (math.exp((rate-q)*dt)-down)/(up-down) if probability is None else probability
    if (probability is None and not 0 < p < 1) or not 0 <= p <= 1:
        raise ValueError("growth must lie strictly between moves, or explicit weight in [0, 1]")
    return int(steps), dt, p


def terminal_binomial_value(spot, strike, rate, maturity, steps, up, down, *, kind="call", q=0, probability=None):
    """European value from terminal state probabilities, without backward induction.

    States run in ascending number of UP moves, unlike trees.binomial_tree.
    An explicit probability is for reproducing rounded source weights; then
    the weighted value need not satisfy exact martingale growth or parity.
    It does not change the domestic discount rate.
    """
    steps, _, p = _binomial_spec(spot, strike, rate, maturity, steps, up, down, q, kind, probability)
    ups = np.arange(steps+1)
    stock = np.exp(math.log(spot)+ups*math.log(up)+(steps-ups)*math.log(down))
    weights = binom.pmf(ups, steps, p)
    payoffs = np.maximum(stock-strike, 0) if kind == "call" else np.maximum(strike-stock, 0)
    price = math.exp(-rate*maturity)*float(weights @ payoffs)
    return dict(stock=stock, weights=weights, payoffs=payoffs, probability=p, price=price)


def small_tree_stopping_values(spot, strike, rate, maturity, steps, up, down, *, kind="call", q=0, probability=None):
    """Enumerate every exercise mask on recombining pre-expiry nodes (N <= 5).

    This independent American reference sums first-exercise cashflows over
    all 2**N paths rather than recursively maximizing continuation values.
    Markov payoffs have an optimum among these node-dependent policies.
    Bits order nodes by time, then number of down moves; root is bit 0.
    Probability overrides have the same rounding meaning as terminal sums.
    """
    steps, dt, p = _binomial_spec(spot, strike, rate, maturity, steps, up, down, q, kind, probability)
    if steps > 5:
        raise ValueError("exhaustive policy method is limited to five steps")
    down_moves = (np.arange(2**steps)[:, None] >> np.arange(steps)) & 1
    downs = np.column_stack((np.zeros(2**steps, dtype=int), down_moves.cumsum(axis=1)))
    times = np.arange(steps+1)
    stock = np.exp(math.log(spot)+(times-downs)*math.log(up)+downs*math.log(down))
    payoffs = np.maximum(stock-strike, 0) if kind == "call" else np.maximum(strike-stock, 0)
    discounted = payoffs*np.exp(-rate*dt*times)
    path_weights = p**(steps-downs[:, -1])*(1-p)**downs[:, -1]
    node_ids = times[:-1]*(times[:-1]+1)//2+downs[:, :-1]
    masks = np.arange(2**(steps*(steps+1)//2))
    selected = ((masks[:, None, None] >> node_ids[None, :, :]) & 1).astype(bool)
    exercise = np.concatenate((selected, np.ones((*selected.shape[:2], 1), dtype=bool)), axis=2)
    first = exercise.argmax(axis=2)
    policy_values = discounted[np.arange(len(path_weights))[None, :], first] @ path_weights
    best = int(policy_values.argmax())
    return dict(price=float(policy_values[best]), best_mask=best,
                policy_values=policy_values, probability=p)
