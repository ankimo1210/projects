"""Private Hull GE Ch15: distributions, replication and pricing identities."""

import math

import numpy as np

from ._stochastic_foundations import gbm_log_law


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
