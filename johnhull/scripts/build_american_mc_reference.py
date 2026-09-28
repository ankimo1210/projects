"""Independent §27.8 reference: Hull's eight paths, exact Bermudan values and seeded simulations.

No hullkit imports. The eight-path example (Tables 27.4-27.7 and the exercise
boundary example) is recomputed with numpy.polyfit and a direct search over the
critical prices. Exact Bermudan values come from quadrature of the lognormal
transition between exercise dates (spacing refined until the value moves by
less than 1e-8), checked against Crank-Nicolson with projection at the dates
and, for three dates, against nested integrals of the Black-Scholes formula.
The American limit comes from CRR, checked against Crank-Nicolson with
projection at every step. Seeded simulations fit each exercise policy on one
sample and value it on a fresh one; the least-squares and boundary code here is
written separately from hullkit's.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy import integrate, optimize, stats
from scipy.linalg import solve_banded
from scipy.signal import fftconvolve

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-27-8/reference.json"
HAND_PATHS = [
    [1.00, 1.09, 1.08, 1.34],
    [1.00, 1.16, 1.26, 1.54],
    [1.00, 1.22, 1.07, 1.03],
    [1.00, 0.93, 0.97, 0.92],
    [1.00, 1.11, 1.56, 1.52],
    [1.00, 0.76, 0.77, 0.90],
    [1.00, 0.92, 0.84, 1.01],
    [1.00, 0.88, 1.22, 1.34],
]
HAND_TIMES = [1.0, 2.0, 3.0]
HAND_RATE = 0.06
HAND_STRIKE = 1.10
PROBLEM_STRIKE = 1.13
PRINTED = {
    "coefficients": {"2": [-1.070, 2.983, -1.813], "1": [2.038, -3.335, 1.356]},
    "continuation": {
        "2": [0.0369, 0.0461, 0.1176, 0.1520, 0.1565],
        "1": [0.0139, 0.1092, 0.2866, 0.1175, 0.1533],
    },
    "value": 0.1144,
    "boundary_averages": {
        "2": [0.0636, 0.0813, 0.1032, 0.0982, 0.0938, 0.0963],
        "1": [0.0972, 0.1008, 0.1283, 0.1202, 0.1215, 0.1228],
    },
    "boundary": {"2": 0.84, "1": 0.88},
    "boundary_value": 0.1208,
}
# Hull's contract with a volatility we assume (the book gives none for the eight paths).
PUT = {"spot": 1.0, "strike": 1.10, "rate": 0.06, "volatility": 0.20, "maturity": 3.0}
DATE_COUNTS = [3, 6, 12, 24, 48]
QUAD_SPACING = (512, 1024)
CN_GRIDS = ((1200, 1200), (2400, 2400))
CRR_STEPS = (20000, 40000)
BIAS_SIZES = [250, 500, 1000, 2000, 4000, 8000, 16000]
BIAS_REPLICATIONS = 200
BIAS_EVALUATION = 10_000
DATES_FIT = 50_000
DATES_EVALUATION = 200_000
SEED = 2708
# Section 15 of the notebook: hullkit.mc.price_american_lsm with 50 exercise dates.
SECTION_15 = {"spot": 50.0, "strike": 50.0, "rate": 0.10, "volatility": 0.40, "maturity": 5 / 12}
SECTION_15_DATES = 50
EXCHANGE = {
    "spots": [100.0, 100.0],
    "rate": 0.05,
    "dividend_yields": [0.06, 0.02],
    "volatilities": [0.20, 0.30],
    "correlation": 0.5,
    "maturity": 1.0,
    "dates": 12,
}


def _put(strike):
    return lambda s: np.maximum(strike - s, 0.0)


# --- Hull's eight paths -------------------------------------------------------------


def hand_least_squares(paths, strike, rate, times, rounded=None):
    """Tables 27.5-27.7 by numpy.polyfit; ``rounded`` replaces the fitted coefficients."""
    paths = np.asarray(paths)
    cash = np.maximum(strike - paths[:, -1], 0.0)
    when = np.full(len(paths), len(times))
    when[cash == 0] = 0
    steps = {}
    for column in range(len(times) - 1, 0, -1):
        exercise = np.maximum(strike - paths[:, column], 0.0)
        itm = np.nonzero(exercise > 0)[0]
        target = np.array(
            [
                cash[i] * math.exp(-rate * (times[when[i] - 1] - times[column - 1]))
                if when[i]
                else 0.0
                for i in itm
            ]
        )
        c, b, a = np.polyfit(paths[itm, column], target, 2)
        coefficients = [a, b, c] if rounded is None else rounded[str(column)]
        spots = paths[itm, column]
        continuation = coefficients[0] + coefficients[1] * spots + coefficients[2] * spots**2
        exercised = itm[exercise[itm] > continuation]
        cash[exercised] = exercise[exercised]
        when[exercised] = column
        steps[str(column)] = {
            "time": times[column - 1],
            "paths": itm.tolist(),
            "spots": spots.tolist(),
            "discounted_continuation": target.tolist(),
            "coefficients": [float(v) for v in coefficients],
            "continuation": continuation.tolist(),
            "exercise_values": exercise[itm].tolist(),
            "exercised": exercised.tolist(),
        }
    table = np.zeros((len(paths), len(times)))
    for i, column in enumerate(when):
        if column:
            table[i, column - 1] = cash[i]
    value = float(
        np.mean(
            [cash[i] * math.exp(-rate * times[w - 1]) if w else 0.0 for i, w in enumerate(when)]
        )
    )
    return {"steps": steps, "cash_flows": table.tolist(), "value": value}


def hand_boundary(paths, strike, rate, times):
    """Hull's boundary search: every candidate S*(t) is tried directly."""
    paths = np.asarray(paths)
    value = np.maximum(strike - paths[:, -1], 0.0)
    when = np.where(value > 0, len(times), 0)
    steps = {}
    for column in range(len(times) - 1, 0, -1):
        continuation = value * math.exp(-rate * (times[column] - times[column - 1]))
        exercise = np.maximum(strike - paths[:, column], 0.0)
        # "-inf" is the never-exercise candidate; "+inf" an interval open above.
        candidates = ["-inf", *sorted(set(paths[exercise > 0, column].tolist()))]
        averages = []
        for c in candidates:
            chosen = (
                (exercise > 0) & (paths[:, column] <= c)
                if c != "-inf"
                else np.zeros(len(paths), bool)
            )
            averages.append(float(np.mean(np.where(chosen, exercise, continuation))))
        best = int(np.argmax(averages))
        threshold = candidates[best]
        chosen = (
            (exercise > 0) & (paths[:, column] <= threshold)
            if threshold != "-inf"
            else np.zeros(len(paths), bool)
        )
        value = np.where(chosen, exercise, continuation)
        when = np.where(chosen, column, when)
        following = candidates[best + 1] if best + 1 < len(candidates) else "+inf"
        steps[str(column)] = {
            "time": times[column - 1],
            "candidates": candidates,
            "averages": averages,
            "threshold": threshold,
            "interval": [threshold, following],
            "values": value.tolist(),
        }
    table = np.zeros((len(paths), len(times)))
    for i, column in enumerate(when):
        if column:
            table[i, column - 1] = max(strike - paths[i, column], 0.0)
    return {
        "steps": steps,
        "cash_flows": table.tolist(),
        "value_at_1": float(value.mean()),
        "value": float(value.mean() * math.exp(-rate * times[0])),
    }


def hand_example():
    lsm = hand_least_squares(HAND_PATHS, HAND_STRIKE, HAND_RATE, HAND_TIMES)
    rounded = hand_least_squares(
        HAND_PATHS, HAND_STRIKE, HAND_RATE, HAND_TIMES, rounded=PRINTED["coefficients"]
    )
    boundary = hand_boundary(HAND_PATHS, HAND_STRIKE, HAND_RATE, HAND_TIMES)
    return {
        "paths": HAND_PATHS,
        "times": HAND_TIMES,
        "rate": HAND_RATE,
        "strike": HAND_STRIKE,
        "exercise_now": HAND_STRIKE - HAND_PATHS[0][0],
        "printed": PRINTED,
        "least_squares": lsm,
        "rounded_coefficients": rounded,
        "boundary": boundary,
        "problem_27_22": {
            "strike": PROBLEM_STRIKE,
            "least_squares": hand_least_squares(HAND_PATHS, PROBLEM_STRIKE, HAND_RATE, HAND_TIMES),
            "boundary": hand_boundary(HAND_PATHS, PROBLEM_STRIKE, HAND_RATE, HAND_TIMES),
        },
    }


# --- Exact Bermudan and American values ---------------------------------------------


def quad_bermudan(spot, strike, rate, dividend, sigma, maturity, dates, call, spacing):
    """Bermudan value by quadrature of the lognormal step between equally spaced dates.

    Log price grid with ``spot`` on a node and, when ``spot != strike``, the
    strike on a node too; the transition density is exact, so the only errors
    are the grid spacing and the kinks of the value at the exercise boundary.
    """
    log_gap = abs(math.log(strike / spot)) or 0.1
    h = log_gap / spacing
    dt = maturity / dates
    drift = (rate - dividend - sigma**2 / 2) * dt
    width = math.ceil((10 * sigma * math.sqrt(maturity) + abs(drift) * dates) / h) + spacing
    x = math.log(spot) + h * np.arange(-width, width + 1)
    payoff = np.maximum(np.exp(x) - strike, 0.0) if call else np.maximum(strike - np.exp(x), 0.0)
    reach = math.ceil((10 * sigma * math.sqrt(dt) + abs(drift)) / h)
    offsets = h * np.arange(-reach, reach + 1)
    density = np.exp(-((-offsets - drift) ** 2) / (2 * sigma**2 * dt)) / math.sqrt(
        2 * math.pi * sigma**2 * dt
    )
    kernel = density * h
    value = payoff.copy()
    for date in range(dates - 1, -1, -1):
        value = math.exp(-rate * dt) * fftconvolve(value, kernel, mode="same")
        if date:
            value = np.maximum(value, payoff)
    return float(value[width])


def cn_bermudan(
    spot,
    strike,
    rate,
    dividend,
    sigma,
    maturity,
    dates,
    call,
    space,
    time,
    exercise_every_step=False,
):
    """Crank-Nicolson in ln S with Rannacher restarts and projection at the exercise dates."""
    centre = math.log(spot)
    half = 8 * sigma * math.sqrt(maturity)
    y = np.linspace(centre - half, centre + half, space + 1)
    h = y[1] - y[0]
    s = np.exp(y)
    payoff = np.maximum(s - strike, 0.0) if call else np.maximum(strike - s, 0.0)
    drift = rate - dividend - sigma**2 / 2
    lower = sigma**2 / (2 * h * h) - drift / (2 * h)
    middle = -(sigma**2) / (h * h) - rate
    upper = sigma**2 / (2 * h * h) + drift / (2 * h)
    per_date = time // dates
    tau = maturity / (per_date * dates)

    def edges(remaining):
        if call:
            return 0.0, s[-1] * math.exp(-dividend * remaining) - strike * math.exp(
                -rate * remaining
            )
        return strike * math.exp(-rate * remaining) - s[0] * math.exp(-dividend * remaining), 0.0

    def advance(values, theta, step, remaining):
        bands = np.zeros((3, space - 1))
        bands[0, 1:] = -theta * step * upper
        bands[1, :] = 1 - theta * step * middle
        bands[2, :-1] = -theta * step * lower
        rhs = values[1:-1] + (1 - theta) * step * (
            lower * values[:-2] + middle * values[1:-1] + upper * values[2:]
        )
        low, high = edges(remaining)
        rhs[0] += theta * step * lower * low
        rhs[-1] += theta * step * upper * high
        new = np.empty_like(values)
        new[1:-1] = solve_banded((1, 1), bands, rhs)
        new[0], new[-1] = low, high
        return new

    values = payoff.copy()
    for date in range(dates - 1, -1, -1):
        for k in range(per_date):
            remaining = tau * (k + 1)
            if k < 2:
                values = advance(
                    advance(values, 1.0, tau / 2, remaining - tau / 2), 1.0, tau / 2, remaining
                )
            else:
                values = advance(values, 0.5, tau, remaining)
            if exercise_every_step and (k < per_date - 1 or date):
                values = np.maximum(values, payoff)
        if date:
            values = np.maximum(values, payoff)
    return float(np.interp(centre, y, values))


def crr_american_put(p, steps):
    dt = p["maturity"] / steps
    up = math.exp(p["volatility"] * math.sqrt(dt))
    prob = (math.exp(p["rate"] * dt) - 1 / up) / (up - 1 / up)
    discount = math.exp(-p["rate"] * dt)
    values = np.maximum(p["strike"] - p["spot"] * up ** (2 * np.arange(steps + 1) - steps), 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * (prob * values[1:] + (1 - prob) * values[:-1])
        values = np.maximum(
            values, p["strike"] - p["spot"] * up ** (2 * np.arange(step + 1) - step)
        )
    return float(values[0])


def bermudan(args, dates, call=False):
    """Quadrature value on the finer spacing, with its refinement change and the CN gap.

    Both must be small relative to the strike (1e-8 and 1e-6).
    """
    quad = [quad_bermudan(*args, dates, call, m) for m in QUAD_SPACING]
    cn = [cn_bermudan(*args, dates, call, space, time) for space, time in CN_GRIDS]
    cn_limit = (4 * cn[1] - cn[0]) / 3
    row = {
        "dates": dates,
        "quadrature_spacing": list(QUAD_SPACING),
        "quadrature": quad,
        "quadrature_change": abs(quad[1] - quad[0]),
        "crank_nicolson": cn,
        "crank_nicolson_extrapolated": cn_limit,
        "crank_nicolson_gap": abs(quad[1] - cn_limit),
        "value": quad[1],
    }
    strike = args[1]
    if row["quadrature_change"] >= 1e-8 * strike or row["crank_nicolson_gap"] >= 1e-6 * strike:
        raise ValueError(f"quadrature is unconverged or disagrees with CN for {dates} dates")
    return row


def black_scholes_put(spot, strike, rate, sigma, maturity):
    d1 = (math.log(spot / strike) + (rate + sigma**2 / 2) * maturity) / (
        sigma * math.sqrt(maturity)
    )
    d2 = d1 - sigma * math.sqrt(maturity)
    return strike * math.exp(-rate * maturity) * stats.norm.cdf(-d2) - spot * stats.norm.cdf(-d1)


def nested_three_dates(p):
    """Three yearly dates: Black-Scholes after the second date, integrals before it."""
    k, r, s = p["strike"], p["rate"], p["volatility"]
    dt = p["maturity"] / 3
    drift = (r - s * s / 2) * dt

    def step(value, spot, boundary):
        """Discounted expectation over one date, split at the exercise boundary."""
        edge = (math.log(boundary / spot) - drift) / (s * math.sqrt(dt))

        def integrand(z):
            return value(spot * math.exp(drift + s * math.sqrt(dt) * z)) * stats.norm.pdf(z)

        options = {"epsabs": 1e-14, "epsrel": 1e-13, "limit": 200}
        below = integrate.quad(integrand, -12, edge, **options)[0]
        above = integrate.quad(integrand, edge, 12, **options)[0]
        return math.exp(-r * dt) * (below + above)

    second = optimize.brentq(
        lambda x: k - x - black_scholes_put(x, k, r, s, dt), 0.3, k - 1e-4, xtol=1e-15
    )

    def at_second(x):
        return k - x if x <= second else black_scholes_put(x, k, r, s, dt)

    first = optimize.brentq(lambda x: k - x - step(at_second, x, second), 0.3, k - 1e-4, xtol=1e-13)

    def at_first(x):
        return k - x if x <= first else step(at_second, x, second)

    return {"boundaries": [first, second], "value": step(at_first, p["spot"], first)}


def american_put(p, crr_steps, cn_grids):
    """CRR (average of N and N+1 steps, extrapolated), checked by CN with projection."""
    args = (p["spot"], p["strike"], p["rate"], 0.0, p["volatility"], p["maturity"])
    crr = [(crr_american_put(p, n) + crr_american_put(p, n + 1)) / 2 for n in crr_steps]
    cn = [
        cn_bermudan(*args, 1, False, space, time, exercise_every_step=True)
        for space, time in cn_grids
    ]
    crr_limit, cn_limit = 2 * crr[1] - crr[0], (4 * cn[1] - cn[0]) / 3
    return {
        "crr_steps": list(crr_steps),
        "crr_averaged": crr,
        "crr_extrapolated": crr_limit,
        "crank_nicolson": cn,
        "crank_nicolson_extrapolated": cn_limit,
        "crank_nicolson_gap": abs(crr_limit - cn_limit),
        "value": crr_limit,
    }


def exact_put(p):
    args = (p["spot"], p["strike"], p["rate"], 0.0, p["volatility"], p["maturity"])
    rows = [bermudan(args, dates) for dates in DATE_COUNTS]
    nested = nested_three_dates(p)
    nested["gap"] = abs(nested["value"] - rows[0]["value"])
    american = american_put(p, CRR_STEPS, ((2000, 4000), (4000, 8000)))
    if nested["gap"] >= 1e-8 or american["crank_nicolson_gap"] >= 5e-6:
        raise ValueError("the exact put references disagree")
    return {"bermudan": rows, "nested_three_dates": nested, "american": american}


def section_15(p=SECTION_15):
    """The comparison put of notebook §15: its 50-date Bermudan floor and American value."""
    args = (p["spot"], p["strike"], p["rate"], 0.0, p["volatility"], p["maturity"])
    row = bermudan(args, SECTION_15_DATES)
    american = american_put(p, (5000, 10000), ((2000, 4000), (4000, 8000)))
    if american["crank_nicolson_gap"] >= 5e-5:
        raise ValueError("the section 15 American references disagree")
    return {"parameters": p, "bermudan": row, "american": american}


# --- Seeded simulations ---------------------------------------------------------------


def put_paths(n, dates, seed, p=PUT):
    """GBM paths at ``dates`` equally spaced exercise times, first column the spot."""
    rng = np.random.default_rng(seed)
    dt = p["maturity"] / dates
    z = rng.standard_normal((n, dates))
    steps = (p["rate"] - p["volatility"] ** 2 / 2) * dt + p["volatility"] * math.sqrt(dt) * z
    return np.column_stack([np.full(n, p["spot"]), p["spot"] * np.exp(np.cumsum(steps, axis=1))])


def exchange_paths(n, seed, p=EXCHANGE):
    """Correlated GBM paths of two assets at the exchange option's exercise dates."""
    rng = np.random.default_rng(seed)
    dt = p["maturity"] / p["dates"]
    z = rng.standard_normal((n, p["dates"], 2))
    rho = p["correlation"]
    shocks = np.stack([z[..., 0], rho * z[..., 0] + math.sqrt(1 - rho**2) * z[..., 1]], axis=2)
    sig = np.array(p["volatilities"])
    drift = (p["rate"] - np.array(p["dividend_yields"]) - sig**2 / 2) * dt
    logs = np.cumsum(drift + sig * math.sqrt(dt) * shocks, axis=1)
    spots = np.array(p["spots"])
    start = np.broadcast_to(spots, (n, 1, 2))
    return np.concatenate([start, spots * np.exp(logs)], axis=1)


def _monomials(states, degree):
    """Monomials of one or two scaled state variables up to ``degree``."""
    if states.ndim == 1:
        return np.column_stack([states**k for k in range(degree + 1)])
    first, second = states[:, 0], states[:, 1]
    return np.column_stack(
        [
            first**i * second ** (total - i)
            for total in range(degree + 1)
            for i in range(total, -1, -1)
        ]
    )


def fit_least_squares(paths, payoff, rate, times, degree=2, scale=1.0):
    """Backward regression of discounted cash flows on in-the-money paths.

    Returns the coefficients (``None`` where fewer in-the-money paths than
    basis functions) and each fitting path's discounted cash flow.
    """
    n = paths.shape[0]
    exercise = [payoff(paths[:, k]) for k in range(paths.shape[1])]
    future = exercise[-1].copy()
    coefficients = [None] * (len(times) - 1)
    stop = np.full(n, len(times))
    for k in range(len(times) - 1, 0, -1):
        future = future * math.exp(-rate * (times[k] - times[k - 1]))
        itm = exercise[k] > 0
        basis = _monomials(paths[itm, k] / scale, degree)
        if itm.sum() < basis.shape[1]:
            continue
        beta, *_ = np.linalg.lstsq(basis, future[itm], rcond=None)
        coefficients[k - 1] = beta
        take = np.zeros(n, bool)
        take[itm] = exercise[k][itm] > basis @ beta
        future[take] = exercise[k][take]
        stop[take] = k
    return coefficients, discounted_stops(stop, exercise, rate, times)


def discounted_stops(stop, exercise, rate, times):
    """Each path's payoff at its stopping date, discounted to time zero."""
    pay = np.column_stack(exercise[1:])[np.arange(stop.size), stop - 1]
    return pay * np.exp(-rate * np.asarray(times)[stop - 1])


def apply_least_squares(coefficients, paths, payoff, rate, times, degree=2, scale=1.0):
    exercise = [payoff(paths[:, k]) for k in range(paths.shape[1])]
    stop = np.full(paths.shape[0], len(times))
    for k in range(len(times) - 1, 0, -1):
        beta = coefficients[k - 1]
        if beta is None:
            continue
        continuation = _monomials(paths[:, k] / scale, degree) @ beta
        stop[(exercise[k] > 0) & (exercise[k] > continuation)] = k
    return discounted_stops(stop, exercise, rate, times)


def fit_boundary(paths, strike, rate, times):
    """Critical prices chosen backward to maximize the mean value (put)."""
    value = np.maximum(strike - paths[:, -1], 0.0)
    stop = np.full(paths.shape[0], len(times))
    boundary = [None] * (len(times) - 1)
    for k in range(len(times) - 1, 0, -1):
        continuation = value * math.exp(-rate * (times[k] - times[k - 1]))
        exercise = np.maximum(strike - paths[:, k], 0.0)
        itm = np.nonzero(exercise > 0)[0]
        order = itm[np.argsort(paths[itm, k], kind="mergesort")]
        gains = np.cumsum(exercise[order] - continuation[order])
        spots = paths[order, k]
        last = np.nonzero(np.append(spots[1:] != spots[:-1], True))[0]
        best = int(np.argmax(np.concatenate([[0.0], gains[last]])))
        threshold = -math.inf if best == 0 else float(spots[last[best - 1]])
        boundary[k - 1] = threshold
        take = (exercise > 0) & (paths[:, k] <= threshold)
        value = np.where(take, exercise, continuation)
        stop[take] = k
    exercise = [np.maximum(strike - paths[:, k], 0.0) for k in range(paths.shape[1])]
    return boundary, discounted_stops(stop, exercise, rate, times)


def apply_boundary(boundary, paths, strike, rate, times):
    exercise = [np.maximum(strike - paths[:, k], 0.0) for k in range(paths.shape[1])]
    stop = np.full(paths.shape[0], len(times))
    for k in range(len(times) - 1, 0, -1):
        stop[(exercise[k] > 0) & (paths[:, k] <= boundary[k - 1])] = k
    return discounted_stops(stop, exercise, rate, times)


def margrabe(p):
    (s1, s2), (q1, q2) = p["spots"], p["dividend_yields"]
    v1, v2 = p["volatilities"]
    v = math.sqrt(v1**2 + v2**2 - 2 * p["correlation"] * v1 * v2)
    t = p["maturity"]
    d1 = (math.log(s1 / s2) + (q2 - q1 + v * v / 2) * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)
    return s1 * math.exp(-q1 * t) * stats.norm.cdf(d1) - s2 * math.exp(-q2 * t) * stats.norm.cdf(d2)


def _estimate(discounted, control, expected):
    """Raw and control-variate means with standard errors (Hull §21.7, eq. 21.20)."""
    n = discounted.size
    adjusted = discounted - (control - expected)
    return {
        "raw": float(discounted.mean()),
        "raw_standard_error": float(discounted.std(ddof=1) / math.sqrt(n)),
        "value": float(adjusted.mean()),
        "standard_error": float(adjusted.std(ddof=1) / math.sqrt(n)),
    }


def _mean(discounted):
    return float(discounted.mean()), float(discounted.std(ddof=1) / math.sqrt(discounted.size))


def bias_study(p, exact):
    """Fit on ``n`` paths and value both on those paths and on fresh ones, many times."""
    times = [p["maturity"] * k / 3 for k in range(1, 4)]
    payoff = _put(p["strike"])
    keys = ("lsm_in", "lsm_out", "boundary_in", "boundary_out")
    out = {
        "sizes": BIAS_SIZES,
        "replications": BIAS_REPLICATIONS,
        "evaluation_paths": BIAS_EVALUATION,
        "dates": 3,
        "exact": exact,
    }
    for key in keys:
        out[key] = {"mean": [], "standard_error": []}
    for n in BIAS_SIZES:
        runs = {key: [] for key in keys}
        for rep in range(BIAS_REPLICATIONS):
            fit = put_paths(n, 3, [SEED, 3, n, rep, 0], p)
            fresh = put_paths(BIAS_EVALUATION, 3, [SEED, 3, n, rep, 1], p)
            coefficients, inside = fit_least_squares(fit, payoff, p["rate"], times)
            runs["lsm_in"].append(inside.mean())
            runs["lsm_out"].append(
                apply_least_squares(coefficients, fresh, payoff, p["rate"], times).mean()
            )
            boundary, inside = fit_boundary(fit, p["strike"], p["rate"], times)
            runs["boundary_in"].append(inside.mean())
            runs["boundary_out"].append(
                apply_boundary(boundary, fresh, p["strike"], p["rate"], times).mean()
            )
        for key in keys:
            mean, error = _mean(np.array(runs[key]))
            out[key]["mean"].append(mean)
            out[key]["standard_error"].append(error)
    return out


def dates_study(p, exact_rows, american):
    """Fit on one sample, value on a fresh one; pair the policies and check the sample.

    The three policies are valued on the same fresh paths, so their differences
    are measured path by path. The fresh paths' discounted European put payoff
    against Black-Scholes shows how lucky each fresh sample is.
    """
    payoff = _put(p["strike"])
    out = {"counts": DATE_COUNTS, "fit_paths": DATES_FIT, "evaluation_paths": DATES_EVALUATION}
    keys = ("lsm2", "lsm3", "boundary")
    for key in keys:
        out[key] = {"in_sample": [], "value": [], "standard_error": []}
    pairs = {"lsm3_minus_lsm2": ("lsm3", "lsm2"), "boundary_minus_lsm2": ("boundary", "lsm2")}
    out["paired"] = {name: {"mean": [], "standard_error": []} for name in pairs}
    european = black_scholes_put(p["spot"], p["strike"], p["rate"], p["volatility"], p["maturity"])
    out["european"] = {"value": european, "mean": [], "standard_error": []}
    for dates in DATE_COUNTS:
        times = [p["maturity"] * k / dates for k in range(1, dates + 1)]
        fit = put_paths(DATES_FIT, dates, [SEED, dates, 0], p)
        fresh = put_paths(DATES_EVALUATION, dates, [SEED, dates, 1], p)
        results = {}
        for key, degree in (("lsm2", 2), ("lsm3", 3)):
            coefficients, inside = fit_least_squares(fit, payoff, p["rate"], times, degree)
            outside = apply_least_squares(coefficients, fresh, payoff, p["rate"], times, degree)
            results[key] = (inside, outside)
        boundary, inside = fit_boundary(fit, p["strike"], p["rate"], times)
        results["boundary"] = (
            inside,
            apply_boundary(boundary, fresh, p["strike"], p["rate"], times),
        )
        for key, (inside, outside) in results.items():
            mean, error = _mean(outside)
            out[key]["in_sample"].append(float(inside.mean()))
            out[key]["value"].append(mean)
            out[key]["standard_error"].append(error)
        for name, (first, second) in pairs.items():
            mean, error = _mean(results[first][1] - results[second][1])
            out["paired"][name]["mean"].append(mean)
            out["paired"][name]["standard_error"].append(error)
        mean, error = _mean(payoff(fresh[:, -1]) * math.exp(-p["rate"] * p["maturity"]))
        out["european"]["mean"].append(mean)
        out["european"]["standard_error"].append(error)
    out["exact"] = [row["value"] for row in exact_rows]
    out["american"] = american["value"]
    return out


def exchange_study(p=EXCHANGE):
    s1, s2 = p["spots"]
    q1, q2 = p["dividend_yields"]
    v1, v2 = p["volatilities"]
    ratio_vol = math.sqrt(v1**2 + v2**2 - 2 * p["correlation"] * v1 * v2)
    ratio = (s1 / s2, 1.0, q2, q1, ratio_vol, p["maturity"])
    row = bermudan(ratio, p["dates"], call=True)
    exact = s2 * row["value"]
    times = [p["maturity"] * k / p["dates"] for k in range(1, p["dates"] + 1)]

    def payoff(states):
        return np.maximum(states[:, 0] - states[:, 1], 0.0)

    euro = margrabe(p)
    fit = exchange_paths(DATES_FIT, [SEED, 99, 0], p)
    fresh = exchange_paths(DATES_EVALUATION, [SEED, 99, 1], p)
    discount = math.exp(-p["rate"] * p["maturity"])
    coefficients, inside = fit_least_squares(fit, payoff, p["rate"], times, 2, scale=100.0)
    outside = apply_least_squares(coefficients, fresh, payoff, p["rate"], times, 2, scale=100.0)
    return {
        "parameters": p,
        "ratio_volatility": ratio_vol,
        "ratio_bermudan": row,
        "exact": exact,
        "european": euro,
        "fit_paths": DATES_FIT,
        "evaluation_paths": DATES_EVALUATION,
        "in_sample": _estimate(inside, payoff(fit[:, -1]) * discount, euro),
        "out_of_sample": _estimate(outside, payoff(fresh[:, -1]) * discount, euro),
    }


def build():
    exact = exact_put(PUT)
    three = next(row["value"] for row in exact["bermudan"] if row["dates"] == 3)
    return {
        "section": "27.8",
        "source": "Hull 11e Global Edition pp.660-665, Tables 27.4-27.7; Longstaff-Schwartz (2001); Andersen (2000)",
        "units": "option prices in the currency of the example; times in years",
        "parameters": {"put": PUT, "seed": SEED},
        "hand_example": hand_example(),
        "exact": exact,
        "bias": bias_study(PUT, three),
        "dates": dates_study(PUT, exact["bermudan"], exact["american"]),
        "exchange": exchange_study(),
        "section_15": section_15(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §27.8 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §27.8 eight paths, exact Bermudan values and seeded simulations")


if __name__ == "__main__":
    main()
