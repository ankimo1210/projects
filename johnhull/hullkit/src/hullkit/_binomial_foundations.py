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


def replication_grid(stock_tree, option_tree, rate, dt):
    """No-dividend stock-bank continuation hedges at every pre-expiry node.

    Levels use trees.binomial_tree's descending stock ordering. If given an
    American tree, the hedge replicates the two next-step option values; its
    continuation value may be below the current immediate exercise value.
    Finite-tree secant deltas are not spot-bump derivatives.
    """
    if len(stock_tree) != len(option_tree) or len(stock_tree) < 2:
        raise ValueError("matching trees with at least one transition required")
    deltas, banks, continuations = [], [], []
    for t in range(len(stock_tree)-1):
        if len(stock_tree[t]) != t+1 or len(stock_tree[t+1]) != t+2 or len(option_tree[t+1]) != t+2:
            raise ValueError("recombining levels must contain time index plus one nodes")
        rows = [one_step_replication(stock_tree[t][j], stock_tree[t+1][j], stock_tree[t+1][j+1],
                                     option_tree[t+1][j], option_tree[t+1][j+1], rate, dt) for j in range(t+1)]
        deltas.append(np.array([r["delta"] for r in rows]))
        banks.append(np.array([r["bank"] for r in rows]))
        continuations.append(np.array([r["price"] for r in rows]))
    return dict(deltas=deltas, bank=banks, continuation=continuations)


def crr_moments(sigma, dt, drift):
    """Two-point return moments versus exact lognormal return moments.

    CRR matches the mean exactly and the variance only to first order in dt.
    Changing P/Q changes probability and finite-step variance; the volatility
    parameter, moves and limiting variance/dt remain the same.
    """
    if not all(math.isfinite(x) for x in (sigma, dt, drift)) or sigma <= 0 or dt <= 0:
        raise ValueError("positive volatility/time and finite drift required")
    up = math.exp(sigma*math.sqrt(dt))
    down = 1/up
    mean = math.exp(drift*dt)
    p = (mean-down)/(up-down)
    if not 0 < p < 1:
        raise ValueError("mean growth must lie between the two moves")
    variance = p*(1-p)*(up-down)**2
    exact = math.exp(2*drift*dt)*math.expm1(sigma*sigma*dt)
    return dict(up=up, down=down, probability=p, mean=mean, variance=variance,
                first_order_variance=sigma*sigma*dt, lognormal_variance=exact,
                variance_error=variance-exact)


def binomial_call_tails(spot, strike, rate, sigma, maturity, steps, *, q=0):
    """Ch13 appendix: cash and stock-numeraire binomial tails, without a tree.

    Exercise uses the strict j > a threshold. A strike whose log distance to
    the nearest terminal node is within 64 eps * max(1, |ln(K/S)|, n) is a
    tie, so strikes rebuilt from node values do not count a zero payoff.
    The stock-numeraire probability is distinct from the physical probability
    in section 13.2. With q != 0, U1's factor is exp((r-q)T).
    """
    if not math.isfinite(sigma) or sigma <= 0 or maturity <= 0 or steps < 1:
        raise ValueError("positive volatility/time/steps required")
    log_move = sigma*math.sqrt(maturity/steps)
    up, down = math.exp(log_move), math.exp(-log_move)
    steps, _, p = _binomial_spec(spot, strike, rate, maturity, steps, up, down, q, "call", None)
    if strike == 0:
        threshold, first = -math.inf, 0
    else:
        threshold = steps/2-math.log(spot/strike)/(2*log_move)
        nearest = round(threshold)
        log_strike = math.log(strike/spot)
        log_gap = (2*nearest-steps)*log_move-log_strike
        if abs(log_gap) <= 64*np.finfo(float).eps*max(1.0, abs(log_strike), steps):
            threshold = float(nearest)
        first = min(max(math.floor(threshold)+1, 0), steps+1)
    stock_p = p*up/(p*up+(1-p)*down)
    cash_tail = float(binom.sf(first-1, steps, p))
    stock_tail = float(binom.sf(first-1, steps, stock_p))
    u1 = math.exp((rate-q)*maturity)*stock_tail
    price = spot*math.exp(-q*maturity)*stock_tail-strike*math.exp(-rate*maturity)*cash_tail
    return dict(price=price, threshold=threshold, first_in_the_money_up_moves=first,
                probability=p, stock_probability=stock_p, cash_tail=cash_tail,
                stock_tail=stock_tail, u1=u1, u2=cash_tail)
