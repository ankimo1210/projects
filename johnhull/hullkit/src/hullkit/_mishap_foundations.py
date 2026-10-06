"""Private Ch37 conditional streak and equal-correlation diversification arithmetic."""

import math


def streak_success(managers, periods, win_probability):
    """Independent periods and managers: single streak, expected count and any success.

    This quantifies the source's random-trading example. An expected count of one
    does not guarantee a winner or establish skill. No incidents are aggregated.
    """
    if (
        min(managers, periods) < 0
        or int(managers) != managers
        or int(periods) != periods
        or not 0 <= win_probability <= 1
    ):
        raise ValueError("nonnegative integer counts and probability in [0,1] required")
    individual = win_probability ** int(periods)
    if managers == 0 or individual == 0:
        any_success = 0.0
    elif individual == 1:
        any_success = 1.0
    else:
        any_success = -math.expm1(managers * math.log1p(-individual))
    return {
        "individual_probability": individual,
        "expected_successes": managers * individual,
        "any_success_probability": any_success,
    }


def equal_correlation_portfolio(count, expected_return, volatility, correlation):
    """Annual moments of equally weighted stocks with identical mean/vol and pair rho.

    Correlation must yield a positive-semidefinite equicorrelation matrix. These
    supplied moments do not guarantee future or stressed correlation stability.
    """
    if (
        count < 1
        or int(count) != count
        or volatility < 0
        or not all(math.isfinite(x) for x in [expected_return, volatility, correlation])
        or not -1 <= correlation <= 1
        or (count > 1 and correlation < -1 / (count - 1))
    ):
        raise ValueError("positive integer stock count, nonnegative vol and feasible rho required")
    variance = volatility**2 * max(correlation + (1 - correlation) / count, 0)
    return {
        "expected_return": expected_return,
        "variance": variance,
        "volatility": math.sqrt(variance),
    }
