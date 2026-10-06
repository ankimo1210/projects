"""Private Hull Ch21: numerical lattices and exercise decisions."""

import math

import numpy as np

from . import trees


def _tree_inputs(spot, strike, rate, sigma, maturity, steps, yield_rate, kind):
    if (
        not all(math.isfinite(x) for x in (spot, strike, rate, sigma, maturity, yield_rate))
        or min(spot, strike, sigma, maturity) <= 0
        or steps < 1
        or int(steps) != steps
        or kind not in {"call", "put"}
    ):
        raise ValueError("positive spot/strike/vol/time, integer steps and call/put required")
    return int(steps)


def _backward(stock, strike, discounts, probabilities, kind, american, before_stock=None):
    """Descending nodes; optional pre-dividend obstacles share the same risky state."""
    steps = len(stock) - 1
    discount = np.broadcast_to(discounts, (steps,))
    probability = np.broadcast_to(probabilities, (steps,))
    if np.any(probability < 0) or np.any(probability > 1):
        raise ValueError("negative branch probability; refine the time grid")
    sign = 1 if kind == "call" else -1
    intrinsic = [np.maximum(sign * (level - strike), 0) for level in stock]
    if before_stock is not None and american:
        intrinsic = [
            np.maximum(after, np.maximum(sign * (before - strike), 0))
            for after, before in zip(intrinsic, before_stock, strict=True)
        ]
    option, continuation, exercise = (
        [None] * (steps + 1),
        [None] * (steps + 1),
        [None] * (steps + 1),
    )
    option[-1] = intrinsic[-1]
    continuation[-1] = intrinsic[-1].copy()
    exercise[-1] = np.zeros_like(intrinsic[-1], dtype=bool)
    for i in range(steps - 1, -1, -1):
        continuation[i] = discount[i] * (
            probability[i] * option[i + 1][:-1] + (1 - probability[i]) * option[i + 1][1:]
        )
        exercise[i] = (intrinsic[i] > continuation[i]) if american else np.zeros(i + 1, dtype=bool)
        option[i] = np.maximum(intrinsic[i], continuation[i]) if american else continuation[i]
    return {
        "price": float(option[0][0]),
        "stock": stock,
        "option": option,
        "continuation": continuation,
        "exercise": exercise,
    }


def crr_lattice(
    spot, strike, rate, sigma, maturity, steps, *, yield_rate=0, kind="call", american=False
):
    """Hull21.1 CRR decisions, with node j=0 highest (opposite the textbook index).

    A diffusive lattice requires positive sigma and T. Exercise flags denote
    strict pre-expiry improvements, not ties or expiry settlement.
    """
    steps = _tree_inputs(spot, strike, rate, sigma, maturity, steps, yield_rate, kind)
    dt = maturity / steps
    up, down = trees.crr_params(sigma, dt)
    p = trees.risk_neutral_p(up, down, rate, dt, yield_rate)
    stock = [
        spot * up ** (i - np.arange(i + 1)) * down ** np.arange(i + 1) for i in range(steps + 1)
    ]
    result = _backward(stock, strike, math.exp(-rate * dt), p, kind, american)
    return {**result, "up": up, "down": down, "probability": p, "dt": dt}


def tree_greek_details(
    spot,
    strike,
    rate,
    sigma,
    maturity,
    steps,
    *,
    yield_rate=0,
    kind="call",
    american=False,
    vol_bump=1e-4,
    rate_bump=1e-4,
):
    """Eq21.8–10 plus one-sided vega/rho bumps at fixed N.

    Delta is estimated at dt, gamma/theta at 2dt and conventionally used at
    t=0. Theta is calendar-time decay. Vega/rho use decimal input units;
    per-point outputs are for a +0.01 change. Bumps are explicit inputs.
    """
    if (
        steps < 2
        or min(vol_bump, rate_bump) <= 0
        or not all(math.isfinite(x) for x in (vol_bump, rate_bump))
    ):
        raise ValueError("at least two levels and positive finite bumps required")
    result = crr_lattice(
        spot,
        strike,
        rate,
        sigma,
        maturity,
        steps,
        yield_rate=yield_rate,
        kind=kind,
        american=american,
    )
    s, v = result["stock"], result["option"]
    delta = (v[1][0] - v[1][1]) / (s[1][0] - s[1][1])
    upper_delta = (v[2][0] - v[2][1]) / (s[2][0] - s[2][1])
    lower_delta = (v[2][1] - v[2][2]) / (s[2][1] - s[2][2])
    gamma = (upper_delta - lower_delta) / ((s[2][0] - s[2][2]) / 2)
    theta = (v[2][1] - v[0][0]) / (2 * result["dt"])
    vol_price = crr_lattice(
        spot,
        strike,
        rate,
        sigma + vol_bump,
        maturity,
        steps,
        yield_rate=yield_rate,
        kind=kind,
        american=american,
    )["price"]
    rate_price = crr_lattice(
        spot,
        strike,
        rate + rate_bump,
        sigma,
        maturity,
        steps,
        yield_rate=yield_rate,
        kind=kind,
        american=american,
    )["price"]
    vega, rho = (vol_price - result["price"]) / vol_bump, (rate_price - result["price"]) / rate_bump
    return {
        "price": result["price"],
        "delta": float(delta),
        "gamma": float(gamma),
        "theta_year": float(theta),
        "theta_day": float(theta / 365),
        "vega": vega,
        "rho": rho,
        "vega_per_point": vega / 100,
        "rho_per_point": rho / 100,
        "delta_time": result["dt"],
        "gamma_time": 2 * result["dt"],
    }


def carry_lattice(
    spot, strike, rate, sigma, maturity, steps, *, asset, yield_rate=0, kind="call", american=False
):
    """Hull21.2 q: index dividend yield, currency foreign rate, or futures r.

    The futures forward growth is one per step; option continuation is still
    discounted at the domestic rate. Yield is ignored for futures by definition.
    """
    if asset not in {"index", "currency", "futures"}:
        raise ValueError("asset must be index, currency or futures")
    effective_yield = rate if asset == "futures" else yield_rate
    result = crr_lattice(
        spot,
        strike,
        rate,
        sigma,
        maturity,
        steps,
        yield_rate=effective_yield,
        kind=kind,
        american=american,
    )
    return {**result, "asset": asset, "effective_yield": effective_yield}


def dividend_lattice(
    spot,
    strike,
    rate,
    sigma,
    maturity,
    steps,
    dividend_times=(),
    dividends=(),
    *,
    model="cash",
    kind="put",
    american=False,
):
    """Hull21.3 recombining cash-S* or proportional-dividend lattice.

    Cash sigma applies to S*=S-PV(D), not total S. Fractions compound as
    product(1-f). Exercise is on the chosen grid; off-grid ex-dates are reported
    and are not silently represented as exact exercise dates. At aligned dates
    an American can exercise immediately before or after the dividend.
    """
    steps = _tree_inputs(spot, strike, rate, sigma, maturity, steps, 0, kind)
    ex = np.asarray(dividend_times, dtype=float)
    amounts = np.asarray(dividends, dtype=float)
    if (
        model not in {"cash", "fraction"}
        or ex.ndim != 1
        or ex.shape != amounts.shape
        or np.any(~np.isfinite(ex))
        or np.any(ex < 0)
        or np.any(~np.isfinite(amounts))
        or np.any(amounts < 0)
        or (model == "fraction" and np.any(amounts >= 1))
    ):
        raise ValueError("matching nonnegative dates/dividends; fractions must be below one")
    inside = ex <= maturity
    ex, amounts = ex[inside], amounts[inside]
    pv = float(amounts @ np.exp(-rate * ex)) if model == "cash" else 0.0
    risky_spot = spot - pv
    if risky_spot < 0:
        raise ValueError("cash dividend PV exceeds spot in the S* model")
    dt = maturity / steps
    up, down = trees.crr_params(sigma, dt)
    probability = trees.risk_neutral_p(up, down, rate, dt)
    epsilon = 1e-12 * max(1, maturity)
    stock, before_stock = [], []
    for i in range(steps + 1):
        time = i * dt
        base = risky_spot * up ** (i - np.arange(i + 1)) * down ** np.arange(i + 1)
        after_mask, before_mask = ex > time + epsilon, ex >= time - epsilon
        if model == "cash":
            reserve = float(amounts[after_mask] @ np.exp(-rate * (ex[after_mask] - time)))
            before_reserve = float(amounts[before_mask] @ np.exp(-rate * (ex[before_mask] - time)))
            stock.append(base + reserve)
            before_stock.append(base + before_reserve)
        else:
            stock.append(base * np.prod(1 - amounts[~after_mask]))
            before_stock.append(base * np.prod(1 - amounts[~before_mask]))
    result = _backward(
        stock, strike, math.exp(-rate * dt), probability, kind, american, before_stock
    )
    off_grid = tuple(float(t) for t in ex if abs(t - dt * round(t / dt)) > epsilon)
    return {
        **result,
        "before_stock": before_stock,
        "risky_spot": risky_spot,
        "dividend_pv": pv,
        "terminal_scale": float(np.prod(1 - amounts)) if model == "fraction" else 1.0,
        "off_grid_dividend_times": off_grid,
        "model": model,
    }


def dividend_control_variate(
    spot,
    strike,
    rate,
    sigma,
    maturity,
    steps,
    dividend_times=(),
    dividends=(),
    *,
    model="cash",
    kind="put",
):
    """Same-model, same-N American-European correction; improvement is not guaranteed."""
    from .bsm import call_price, put_price

    arguments = (spot, strike, rate, sigma, maturity, steps, dividend_times, dividends)
    american = dividend_lattice(*arguments, model=model, kind=kind, american=True)
    european = dividend_lattice(*arguments, model=model, kind=kind)
    adjusted_spot = european["risky_spot"] * european["terminal_scale"]
    if adjusted_spot == 0:
        reference = strike * math.exp(-rate * maturity) if kind == "put" else 0.0
    else:
        reference = float(
            (call_price if kind == "call" else put_price)(
                adjusted_spot, strike, rate, sigma, maturity
            )
        )
    return {
        "american": american["price"],
        "european_tree": european["price"],
        "european_reference": reference,
        "corrected": american["price"] + reference - european["price"],
    }
