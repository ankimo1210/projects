"""Private Hull Ch21: Monte Carlo sample replay and estimator statistics."""

import math

import numpy as np


def summary_from_stats(mean, sample_std, count, *, interval_se_digits=None):
    """IID-trial SE and asymptotic normal 95% interval; raw SE is always retained.

    Optional prior SE rounding reproduces Example21.8's display arithmetic. This
    function does not reconstruct the random sample from quoted statistics.
    """
    if (
        not all(math.isfinite(x) for x in (mean, sample_std))
        or sample_std < 0
        or count < 2
        or int(count) != count
    ):
        raise ValueError("finite mean/nonnegative SD and at least two trials required")
    se = sample_std / math.sqrt(count)
    interval_se = se if interval_se_digits is None else round(se, interval_se_digits)
    return {
        "estimate": mean,
        "sample_std": sample_std,
        "standard_error": se,
        "interval_standard_error": interval_se,
        "confidence95": (mean - 1.96 * interval_se, mean + 1.96 * interval_se),
        "count": int(count),
    }


def iid_summary(samples):
    """One independent trial per supplied sample; not raw antithetic/QMC points."""
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 1 or samples.size < 2 or np.any(~np.isfinite(samples)):
        raise ValueError("at least two finite independent-trial values required for SE")
    return {
        **summary_from_stats(float(samples.mean()), float(samples.std(ddof=1)), samples.size),
        "samples": samples,
    }


def pi_from_points(points):
    """Snapshot21.1's unit-square dart statistic, four times the circle indicator."""
    points = np.asarray(points, dtype=float)
    if (
        points.ndim != 2
        or points.shape[1] != 2
        or np.any(~np.isfinite(points))
        or np.any(points < 0)
        or np.any(points > 1)
    ):
        raise ValueError("finite unit-square points required")
    return iid_summary(4 * np.asarray(np.sum((points - 0.5) ** 2, axis=1) < 0.25, dtype=float))


def gbm_paths_from_normals(spot, rate, sigma, maturity, normals, *, yield_rate=0, scheme="exact"):
    """Replay supplied shocks with Q drift r-q; rows paths, columns intervals.

    Shares the Ch14 exact/Euler primitive. Euler negative outcomes are retained.
    No RNG is hidden inside this function, so callers can reuse identical shocks.
    """
    from ._stochastic_foundations import stock_paths

    z = np.atleast_2d(np.asarray(normals, dtype=float))
    if z.ndim != 2 or z.shape[1] < 1:
        raise ValueError("path-by-step shocks with at least one interval required")
    return stock_paths(spot, rate - yield_rate, sigma, maturity / z.shape[1], z, scheme=scheme)


def european_mc_from_normals(
    spot, strike, rate, sigma, maturity, normals, *, yield_rate=0, kind="call", scheme="exact"
):
    """European discounted IID payoff samples and their correctly discounted SE."""
    if not math.isfinite(strike) or kind not in {"call", "put"}:
        raise ValueError("finite strike and call/put required")
    paths = gbm_paths_from_normals(
        spot, rate, sigma, maturity, normals, yield_rate=yield_rate, scheme=scheme
    )
    sign = 1 if kind == "call" else -1
    samples = math.exp(-rate * maturity) * np.maximum(sign * (paths[:, -1] - strike), 0)
    result = iid_summary(samples)
    return {**result, "price": result["estimate"], "discounted_payoffs": samples}


def tree_sample_paths(spot, sigma, maturity, move_strings):
    """Deterministically replay U/D CRR paths, including initial and final stocks.

    A supplied list such as Table21.3 is an illustrative sample, not a complete
    risk-neutral distribution and not an exact Asian-option price.
    """
    from ._stochastic_foundations import _stock_inputs

    _stock_inputs(spot, 0, sigma, maturity)
    moves = list(move_strings)
    if (
        not moves
        or len(moves[0]) < 1
        or any(len(m) != len(moves[0]) or set(m) - {"U", "D"} for m in moves)
    ):
        raise ValueError("equal-length nonempty U/D paths required")
    steps = len(moves[0])
    signs = np.array([[1 if m == "U" else -1 for m in path] for path in moves])
    log_moves = sigma * math.sqrt(maturity / steps) * signs
    return spot * np.exp(np.column_stack((np.zeros(len(moves)), np.cumsum(log_moves, axis=1))))


def arithmetic_asian_details(paths, strike, rate, maturity, *, include_initial=True, kind="call"):
    """Table21.3's equally weighted observations; initial stock is included by default."""
    paths = np.asarray(paths, dtype=float)
    if (
        paths.ndim != 2
        or paths.shape[1] < 2
        or np.any(~np.isfinite(paths))
        or not all(math.isfinite(x) for x in (strike, rate, maturity))
        or maturity < 0
        or kind not in {"call", "put"}
    ):
        raise ValueError("finite path observations, nonnegative time and call/put required")
    averages = paths.mean(axis=1) if include_initial else paths[:, 1:].mean(axis=1)
    sign = 1 if kind == "call" else -1
    payoffs = np.maximum(sign * (averages - strike), 0)
    discounted = math.exp(-rate * maturity) * payoffs
    result = iid_summary(discounted)
    return {
        **result,
        "price": result["estimate"],
        "averages": averages,
        "payoffs": payoffs,
        "discounted_payoffs": discounted,
    }


def correlate_normals(normals, correlation):
    """Eq21.19 Cholesky transform; spectral factor for a valid singular PSD matrix."""
    z, correlation = np.asarray(normals, dtype=float), np.asarray(correlation, dtype=float)
    if (
        correlation.ndim != 2
        or correlation.shape[0] != correlation.shape[1]
        or z.ndim < 1
        or z.shape[-1] != len(correlation)
        or np.any(~np.isfinite(z))
        or np.any(~np.isfinite(correlation))
        or not np.allclose(correlation, correlation.T, rtol=0, atol=1e-12)
        or not np.allclose(np.diag(correlation), 1, rtol=0, atol=1e-12)
    ):
        raise ValueError("symmetric unit-diagonal correlation and matching finite shocks required")
    try:
        factor = np.linalg.cholesky(correlation)
    except np.linalg.LinAlgError:
        values, vectors = np.linalg.eigh(correlation)
        if values.min() < -1e-12:
            raise ValueError("correlation matrix is not positive semidefinite") from None
        factor = vectors * np.sqrt(np.maximum(values, 0))
    return {"normals": z @ factor.T, "factor": factor}


def common_random_greek(
    spot, strike, rate, sigma, maturity, normals, *, parameter, bump, yield_rate=0, kind="call"
):
    """One-sided Greek and SE from paired payoff differences using identical shocks.

    Fixed path count and time grid, fixed yield rate even for a rate bump. Units
    are per spot unit, per 1.0 volatility, or per 1.0 domestic interest rate.
    """
    if parameter not in {"spot", "rate", "sigma"} or not math.isfinite(bump) or bump == 0:
        raise ValueError("spot/rate/sigma parameter and finite nonzero bump required")
    base = european_mc_from_normals(
        spot, strike, rate, sigma, maturity, normals, yield_rate=yield_rate, kind=kind
    )
    changed = {"spot": spot, "rate": rate, "sigma": sigma}
    changed[parameter] += bump
    shifted = european_mc_from_normals(
        changed["spot"],
        strike,
        changed["rate"],
        changed["sigma"],
        maturity,
        normals,
        yield_rate=yield_rate,
        kind=kind,
    )
    return iid_summary((shifted["discounted_payoffs"] - base["discounted_payoffs"]) / bump)
