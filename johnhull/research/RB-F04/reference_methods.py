"""Independent numerical references for RB-F04 Heston/local-volatility dynamics.

The calendar-time log-price PDE and separately written Heston characteristic
function do not import hullkit. Prices are synthetic, in currency; time is in
years and variance is an annualized variance rate.
"""

import math
from collections import Counter

import numpy as np
from scipy.linalg import solve_banded


def pde_call(
    spot,
    strikes,
    T,
    variance,
    rate,
    q,
    space_nodes=601,
    time_steps=384,
    log_half_width=1.5,
):
    """Price calls by a backward log-price CN scheme with Rannacher damping.

    variance(t, spots) returns a dict with broadcastable variance and string
    status arrays. Calendar time is strictly positive at every coefficient
    evaluation. The first backward interval consists of two fully implicit
    half steps, each evaluated at its own midpoint; later intervals use
    Crank-Nicolson. No variance or price clipping is performed.

    Return prices, support/failure information, evaluated status counts and
    the spatial grid (including final call values, one row per strike).
    Unsupported statuses (prefixed unsupported), negative variance and
    nonfinite variance make every returned price NaN. Input contract errors
    raise ValueError.

    The finite domain supports only strikes whose discounted intrinsic value
    keeps the upper boundary ITM/nonnegative and the zero lower boundary OTM
    for every backward time tau in [0,T]: min_tau Smax*exp((r-q)*tau) >= max(K)
    and max_tau Smin*exp((r-q)*tau) <= min(K). Outside this scope return
    unsupported_domain before evaluating variance, rather than clip a boundary.
    These are necessary boundary assumptions, not an error bound: callers must
    still enlarge the domain independently to assess truncation error.
    """
    strikes = np.atleast_1d(np.asarray(strikes, dtype=float))
    if (
        strikes.ndim != 1
        or strikes.size == 0
        or np.any(~np.isfinite(strikes))
        or np.any(strikes <= 0)
        or not all(np.isfinite(v) for v in (spot, T, rate, q, log_half_width))
        or spot <= 0
        or T <= 0
        or log_half_width <= 0
        or not isinstance(space_nodes, (int, np.integer))
        or isinstance(space_nodes, bool)
        or space_nodes < 5
        or not isinstance(time_steps, (int, np.integer))
        or isinstance(time_steps, bool)
        or time_steps < 1
        or not callable(variance)
    ):
        raise ValueError("finite positive spot, strikes, expiry and a valid PDE grid are required")

    x = np.linspace(math.log(spot) - log_half_width, math.log(spot) + log_half_width, space_nodes)
    spots = np.exp(x)
    dx = x[1] - x[0]
    dt = T / time_steps
    values = np.maximum(spots[:, None] - strikes[None, :], 0.0)
    statuses = Counter()
    evaluation_times = []
    negative_operator_coefficients = 0
    tau = 0.0
    minimum_forward_upper = spots[-1] * math.exp(min(0.0, (rate - q) * T))
    maximum_forward_lower = spots[0] * math.exp(max(0.0, (rate - q) * T))
    domain_failure = (
        "upper_boundary"
        if minimum_forward_upper < strikes.max()
        else "lower_boundary"
        if maximum_forward_lower > strikes.min()
        else None
    )
    failure = "unsupported_domain" if domain_failure is not None else None
    if failure is not None:
        statuses.update({failure: 1})

    def step(tau_new, increment, implicit_weight):
        nonlocal values, negative_operator_coefficients
        calendar_time = T - (tau_new - increment / 2)
        evaluation_times.append(calendar_time)
        coefficients = variance(calendar_time, spots[1:-1])
        if not isinstance(coefficients, dict) or not {"variance", "status"} <= coefficients.keys():
            raise ValueError("variance must return a dict containing variance and status")
        try:
            var = np.broadcast_to(
                np.asarray(coefficients["variance"], dtype=float), (space_nodes - 2,)
            )
            status = np.broadcast_to(
                np.asarray(coefficients["status"], dtype=str), (space_nodes - 2,)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("variance and status must match the interior spatial grid") from exc
        labels, counts = np.unique(status, return_counts=True)
        statuses.update(dict(zip(labels.tolist(), counts.tolist(), strict=True)))
        if any(label.startswith("unsupported") for label in labels):
            return "unsupported_variance"
        if np.any(~np.isfinite(var)):
            return "nonfinite_variance"
        if np.any(var < 0):
            return "negative_variance"

        diffusion = 0.5 * var / dx**2
        drift = (rate - q - 0.5 * var) / (2 * dx)
        low, middle, up = diffusion - drift, -2 * diffusion - rate, diffusion + drift
        negative_operator_coefficients += int(np.count_nonzero(low < 0) + np.count_nonzero(up < 0))
        rhs = values[1:-1] + (1 - implicit_weight) * increment * (
            low[:, None] * values[:-2] + middle[:, None] * values[1:-1] + up[:, None] * values[2:]
        )
        lower_boundary = np.zeros_like(strikes)
        upper_boundary = spots[-1] * math.exp(-q * tau_new) - strikes * math.exp(-rate * tau_new)
        rhs[0] += implicit_weight * increment * low[0] * lower_boundary
        rhs[-1] += implicit_weight * increment * up[-1] * upper_boundary
        bands = np.zeros((3, space_nodes - 2))
        bands[0, 1:] = -implicit_weight * increment * up[:-1]
        bands[1] = 1 - implicit_weight * increment * middle
        bands[2, :-1] = -implicit_weight * increment * low[1:]
        updated = np.empty_like(values)
        updated[1:-1] = solve_banded((1, 1), bands, rhs)
        updated[0], updated[-1] = lower_boundary, upper_boundary
        if np.any(~np.isfinite(updated)):
            return "nonfinite_solution"
        values = updated
        return None

    for index in range(time_steps):
        if failure is not None:
            break
        increments = (dt / 2, dt / 2) if index == 0 else (dt,)
        weight = 1.0 if index == 0 else 0.5
        for increment in increments:
            failure = step(tau + increment, increment, weight)
            if failure is not None:
                break
            tau += increment
        if failure is not None:
            break

    price = (
        np.array([np.interp(math.log(spot), x, row) for row in values.T])
        if failure is None
        else np.full(strikes.shape, np.nan)
    )
    return {
        "price": price,
        "supported": failure is None,
        "failure": failure,
        "status_counts": dict(statuses),
        "grid": {
            "space_nodes": int(space_nodes),
            "time_steps": int(time_steps),
            "log_half_width": float(log_half_width),
            "log_spots": x,
            "spots": spots,
            "values": values.T,
            "min_calendar_time": min(evaluation_times) if evaluation_times else float("nan"),
            "max_calendar_time": max(evaluation_times) if evaluation_times else float("nan"),
            "coefficient_evaluations": len(evaluation_times),
            "rannacher_half_steps": min(2, len(evaluation_times)),
            "negative_operator_coefficients": negative_operator_coefficients,
            "backward_time_completed": tau,
            **(
                {
                    "domain_failure": domain_failure,
                    "minimum_forward_upper": float(minimum_forward_upper),
                    "maximum_forward_lower": float(maximum_forward_lower),
                }
                if domain_failure is not None
                else {}
            ),
        },
    }


def _integrated_variance(parameters, T):
    kappa = parameters["kappa"]
    if kappa == 0:
        return parameters["v0"] * T
    return (
        parameters["theta"] * T
        + (parameters["v0"] - parameters["theta"]) * (-math.expm1(-kappa * T)) / kappa
    )


def _log_price_cf(u, T, parameters):
    """Own trap-stable Heston transform of log S_T, with the xi=0 limit."""
    p = parameters
    phase = 1j * u * (math.log(p["spot"]) + (p["rate"] - p["dividend_yield"]) * T)
    if p["xi"] == 0:
        integrated = _integrated_variance(p, T)
        return np.exp(phase - 0.5 * (u * u + 1j * u) * integrated)
    xi = p["xi"]
    b = p["kappa"] - 1j * p["rho"] * xi * u
    d = np.sqrt(b * b + xi * xi * (u * u + 1j * u))
    g = (b - d) / (b + d)
    decay = np.exp(-d * T)
    c = p["kappa"] * p["theta"] / xi**2 * ((b - d) * T - 2 * np.log((1 - g * decay) / (1 - g)))
    loading = (b - d) / xi**2 * (1 - decay) / (1 - g * decay)
    return np.exp(phase + c + loading * p["v0"])


def independent_heston_call(strikes, T, parameters, upper=250.0):
    """Price calls using two own-CF Gil-Pelaez probability integrals.

    Parameters may be a mapping or an object with spot, rate, dividend_yield,
    v0, kappa, theta, xi and rho attributes. The formula is independently
    transcribed from the existing research reference in
    scripts/build_stochastic_volatility_reference.py, without importing it
    or any hullkit transform. The finite integration upper bound is explicit;
    callers compare separate bounds to diagnose truncation.

    xi=0 uses the exact integrated deterministic variance in the own CF.
    The zero-integrated-variance case returns discounted intrinsic value.
    """
    from collections.abc import Mapping

    from scipy.integrate import quad

    names = ("spot", "rate", "dividend_yield", "v0", "kappa", "theta", "xi", "rho")
    try:
        p = {
            key: float(
                parameters[key] if isinstance(parameters, Mapping) else getattr(parameters, key)
            )
            for key in names
        }
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Heston parameters must expose all finite model fields") from exc
    strikes = np.atleast_1d(np.asarray(strikes, dtype=float))
    if (
        not all(np.isfinite(v) for v in (*p.values(), T, upper))
        or p["spot"] <= 0
        or min(p["v0"], p["kappa"], p["theta"], p["xi"]) < 0
        or abs(p["rho"]) > 1
        or T <= 0
        or upper <= 0
        or strikes.ndim != 1
        or strikes.size == 0
        or np.any(~np.isfinite(strikes))
        or np.any(strikes <= 0)
    ):
        raise ValueError(
            "finite positive market/integration inputs and valid Heston parameters required"
        )
    discount_stock = p["spot"] * math.exp(-p["dividend_yield"] * T)
    discount = math.exp(-p["rate"] * T)
    if _integrated_variance(p, T) == 0:
        return np.maximum(discount_stock - strikes * discount, 0.0)

    # E[S_T] is known analytically, including cases where the -i CF formula
    # itself has a removable singularity. It normalizes the stock measure.
    stock_moment = p["spot"] * math.exp((p["rate"] - p["dividend_yield"]) * T)
    settings = {"limit": 800, "epsabs": 1e-12, "epsrel": 1e-11}
    prices = []
    for strike in strikes:
        log_k = math.log(strike)

        def stock_probability_integrand(u, log_k=log_k):
            return (
                np.exp(-1j * u * log_k) * _log_price_cf(u - 1j, T, p) / (1j * u * stock_moment)
            ).real

        def money_probability_integrand(u, log_k=log_k):
            return (np.exp(-1j * u * log_k) * _log_price_cf(u, T, p) / (1j * u)).real

        p1 = 0.5 + quad(stock_probability_integrand, 0.0, upper, **settings)[0] / math.pi
        p2 = 0.5 + quad(money_probability_integrand, 0.0, upper, **settings)[0] / math.pi
        prices.append(discount_stock * p1 - strike * discount * p2)
    return np.array(prices)
