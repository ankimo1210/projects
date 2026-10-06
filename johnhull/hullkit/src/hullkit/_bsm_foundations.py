"""Private Hull GE Ch15: distributions, replication and pricing identities."""

import math

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
