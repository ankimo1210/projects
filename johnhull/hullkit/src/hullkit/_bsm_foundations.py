"""Private Hull GE Ch15: distributions, replication and pricing identities."""

import math

import numpy as np

from . import bsm
from ._stochastic_foundations import gbm_log_law, ito_coefficients


def stock_distribution(spot, drift, sigma, maturity):
    """Price and log-price moments under a caller-supplied GBM drift."""
    law = gbm_log_law(spot, drift, sigma, maturity)
    return {
        "log_mean": law["log_mean"],
        "log_variance": law["log_variance"],
        "log_sd": math.sqrt(law["log_variance"]),
        "price_mean": law["mean"],
        "price_variance": law["variance"],
        "price_sd": math.sqrt(law["variance"]),
    }


def lognormal_interval(log_mean, log_sd, *, z=1.96):
    """Central interval; default z is Hull's approximate 95% halfwidth.

    The caller may supply printed intermediate moments to reproduce source
    rounding. Raw distribution moments give a different, unrounded interval.
    """
    if not all(math.isfinite(x) for x in (log_mean, log_sd, z)) or log_sd < 0 or z < 0:
        raise ValueError("finite log mean and nonnegative standard deviation/z required")
    return math.exp(log_mean-z*log_sd), math.exp(log_mean+z*log_sd)


def return_distribution(drift, sigma, maturity):
    """Law of log(S_T/S_0)/T, an annualized realized rate, not stock drift."""
    if maturity <= 0:
        raise ValueError("average return requires positive maturity")
    law = gbm_log_law(1, drift, sigma, maturity)
    variance = law["log_variance"]/maturity**2
    return {"mean": law["log_mean"]/maturity, "variance": variance, "sd": math.sqrt(variance)}


def realized_return_summary(initial, simple_returns):
    """Annual simple returns with reinvestment and no external cashflows."""
    returns = tuple(simple_returns)
    if not math.isfinite(initial) or initial <= 0 or not returns or any(not math.isfinite(r) or r < -1 for r in returns):
        raise ValueError("positive initial wealth and nonempty finite returns >= -1 required")
    balances = [initial]
    for r in returns:
        balances.append(balances[-1]*(1+r))
    arithmetic = math.fsum(returns)/len(returns)
    return {
        "balances": balances,
        "arithmetic_mean": arithmetic,
        "geometric_mean": math.prod(1+r for r in returns)**(1/len(returns))-1,
        "constant_mean_final": initial*(1+arithmetic)**len(returns),
    }


def historical_volatility(prices, interval_years, *, dividends=None):
    """Sample log-return volatility (n-1) and Hull's approximate sigma SE.

    Dividend cash belongs to each ending interval. The caller chooses time
    units and which observations to retain; adjustment never removes a row.
    """
    prices = np.asarray(prices, dtype=float)
    if prices.ndim != 1 or len(prices) < 3 or not np.all(np.isfinite(prices)) or np.any(prices <= 0) or not math.isfinite(interval_years) or interval_years <= 0:
        raise ValueError("at least three positive prices and positive interval required")
    cash = np.zeros(len(prices)-1) if dividends is None else np.asarray(dividends, dtype=float)
    if cash.shape != (len(prices)-1,) or not np.all(np.isfinite(cash)) or np.any(cash < 0):
        raise ValueError("one nonnegative dividend per return interval required")
    relatives = (prices[1:]+cash)/prices[:-1]
    returns = np.log(relatives)
    sd = float(returns.std(ddof=1))
    annual = sd/math.sqrt(interval_years)
    return {
        "price_relatives": relatives,
        "log_returns": returns,
        "sum_returns": float(returns.sum()),
        "sum_squares": float(returns@returns),
        "interval_sd": sd,
        "annual_vol": annual,
        "vol_se": annual/math.sqrt(2*len(returns)),
    }


def delta_hedge_cash(option_units, delta, stock_change, option_change, rebalance_spot, next_delta):
    """Mark-to-market P&L and instantaneous, self-financing hedge trade.

    Negative option_units denotes sold options. P&L excludes financing over
    time; a finite move need not cancel. Rebalance cash is a transfer, not P&L.
    """
    if not all(math.isfinite(x) for x in (option_units, delta, stock_change, option_change, rebalance_spot, next_delta)) or rebalance_spot <= 0:
        raise ValueError("finite positions/moves and positive rebalance spot required")
    stock_units = -option_units*delta
    option_pnl = option_units*option_change
    stock_pnl = stock_units*stock_change
    trade = -option_units*next_delta-stock_units
    return {
        "stock_units": stock_units,
        "option_pnl": option_pnl,
        "stock_pnl": stock_pnl,
        "pnl": option_pnl+stock_pnl,
        "rebalance_units": trade,
        "rebalance_cash": -trade*rebalance_spot,
    }


def bsm_pde_residual(spot, rate, sigma, value, f_time, f_spot, f_spot_spot):
    """Left minus right of (15.16); f_time is the calendar-time derivative."""
    if not all(math.isfinite(x) for x in (spot, rate, sigma, value, f_time, f_spot, f_spot_spot)) or spot <= 0 or sigma < 0:
        raise ValueError("finite derivatives, positive spot and nonnegative volatility required")
    return f_time+rate*spot*f_spot+.5*sigma**2*spot**2*f_spot_spot-rate*value


def delta_hedged_coefficients(spot, drift, sigma, f_time, delta, gamma):
    """Itô drift/diffusion of df-delta*dS, holding delta locally fixed."""
    gbm_log_law(spot, drift, sigma, 0)
    a, b = ito_coefficients(drift*spot, sigma*spot, f_time, delta, gamma)
    return float(a-delta*drift*spot), float(b-delta*sigma*spot)


def forward_contract_value(spot, strike, rate, maturity):
    """No-dividend forward contract value, distinct from the delivery price."""
    gbm_log_law(spot, rate, 0, maturity)
    if not math.isfinite(strike):
        raise ValueError("finite delivery price required")
    return spot-strike*math.exp(-rate*maturity)


def inverse_stock_value(spot, rate, sigma, maturity):
    """Risk-neutral present value of the terminal payment 1/S_T."""
    gbm_log_law(spot, rate, sigma, maturity)
    return math.exp((sigma**2-2*rate)*maturity)/spot


def perpetual_hit_value(spot, barrier, payment, rate, sigma):
    """Payment at the first continuous hit of H, no yield, r>0 and sigma>0.

    Boundary values are zero at S=0/infinity and payment at S=H; a contract
    that never hits pays nothing. Negative rates are outside this solution.
    """
    if not all(math.isfinite(x) for x in (spot, barrier, payment, rate, sigma)) or min(spot, barrier, rate, sigma) <= 0 or payment < 0:
        raise ValueError("positive spot/barrier/rate/volatility and nonnegative payment required")
    return payment*spot/barrier if spot <= barrier else payment*(spot/barrier)**(-2*rate/sigma**2)


def bsm_call_decomposition(spot, strike, rate, sigma, maturity):
    """No-dividend call, Q exercise probability and truncated first moment.

    The event is S_T>K. N(d1) is a stock weight, not its Q probability.
    Conditional mean is None for a zero-probability event. Singular d values
    at zero time/volatility/strike are represented by None.
    """
    law = gbm_log_law(spot, rate, sigma, maturity)
    if not math.isfinite(strike) or strike < 0:
        raise ValueError("nonnegative finite strike required")
    mean = law["mean"]
    d_first = d_second = None
    if strike == 0:
        probability = weight = 1.0
        price = spot
    elif sigma == 0 or maturity == 0:
        probability = weight = float(mean > strike)
        price = math.exp(-rate*maturity)*max(mean-strike, 0)
    else:
        d_first = float(bsm.d1(spot, strike, rate, sigma, maturity))
        d_second = float(bsm.d2(spot, strike, rate, sigma, maturity))
        probability = standard_normal_probability(d_second)
        weight = standard_normal_probability(d_first)
        price = float(bsm.call_price(spot, strike, rate, sigma, maturity))
    truncated = mean*weight
    return {
        "price": price,
        "d1": d_first,
        "d2": d_second,
        "exercise_probability": probability,
        "stock_weight": weight,
        "truncated_mean": truncated,
        "conditional_mean": truncated/probability if probability > 0 else None,
    }


def standard_normal_probability(x, *, upper=False):
    """Standard normal CDF or direct upper tail; infinities give limits."""
    if math.isnan(x):
        raise ValueError("normal probability is undefined for NaN")
    return math.erfc((x if upper else -x)/math.sqrt(2))/2


def _share_counts(old_shares, new_rights):
    if not all(math.isfinite(x) for x in (old_shares, new_rights)) or old_shares <= 0 or new_rights < 0:
        raise ValueError("positive existing shares and nonnegative new rights required")


def new_warrant_issue(spot, strike, rate, sigma, maturity, old_shares, new_rights):
    """Hull Ex15.7 planned-issue cost with unaffected pre-announcement spot.

    Each right purchases one new share. The source assumes no offsetting
    benefit from the issue; this is not another haircut to an announced spot.
    """
    _share_counts(old_shares, new_rights)
    call = bsm_call_decomposition(spot, strike, rate, sigma, maturity)["price"]
    factor = old_shares/(old_shares+new_rights)
    warrant = factor*call
    cost = new_rights*warrant
    return {"ordinary_call": call, "dilution_factor": factor, "warrant_price": warrant, "issue_cost": cost, "post_issue_spot": spot-cost/old_shares}


def new_issue_terminal_allocation(unaffected_spot, strike, old_shares, new_rights):
    """Terminal assets/capital allocation in the planned-issue model.

    unaffected_spot means assets before exercise divided by old shares,
    excluding the warrant liability. It is not an already-announced quote.
    """
    _share_counts(old_shares, new_rights)
    if not all(math.isfinite(x) for x in (unaffected_spot, strike)) or unaffected_spot <= 0 or strike < 0:
        raise ValueError("positive unaffected stock value and nonnegative strike required")
    exercise = unaffected_spot > strike
    proceeds = new_rights*strike if exercise else 0.0
    shares = old_shares+new_rights if exercise else old_shares
    stock = (old_shares*unaffected_spot+proceeds)/shares
    return {"post_exercise_spot": stock, "warrant_payoff": max(stock-strike, 0), "exercise_proceeds": proceeds}


def implied_vol_bisection(price, spot, strike, rate, maturity, *, kind="call", price_tolerance=1e-10):
    """Scalar BSM IV by bisection, with finite-root arbitrage bounds.

    At the deterministic lower bound choose sigma=0; at the upper bound no
    finite root exists. Expiry and zero strike do not identify volatility.
    """
    gbm_log_law(spot, rate, 0, maturity)
    if maturity <= 0 or not math.isfinite(strike) or strike <= 0 or kind not in ("call", "put") or not math.isfinite(price) or not math.isfinite(price_tolerance) or price_tolerance <= 0:
        raise ValueError("positive expiry/strike/tolerance and finite call or put price required")
    pricing = bsm.call_price if kind == "call" else bsm.put_price
    lower = float(pricing(spot, strike, rate, 0, maturity))
    upper = spot if kind == "call" else strike*math.exp(-rate*maturity)
    if price < lower or price >= upper:
        raise ValueError("price outside finite-IV arbitrage bounds")
    if price-lower <= price_tolerance:
        return 0.0
    lo, hi = 0.0, .5
    while float(pricing(spot, strike, rate, hi, maturity)) < price:
        hi *= 2
    for _ in range(160):
        mid = (lo+hi)/2
        error = float(pricing(spot, strike, rate, mid, maturity))-price
        if abs(error) <= price_tolerance or mid == lo or mid == hi:
            return mid
        if error < 0:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def quoted_futures_pnl(entry_quote, exit_quote, multiplier, *, quantity=1):
    """Futures quote difference times currency per quote point and position."""
    if not all(math.isfinite(x) for x in (entry_quote, exit_quote, multiplier, quantity)) or multiplier <= 0:
        raise ValueError("finite quotes/position and positive quote multiplier required")
    return quantity*multiplier*(exit_quote-entry_quote)
