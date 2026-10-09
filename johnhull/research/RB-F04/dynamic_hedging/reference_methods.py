"""Independent numerical references for RB-F04 Heston/local-volatility dynamics.

The calendar-time log-price PDE and separately written Heston characteristic
function do not import hullkit. Prices are synthetic, in currency; time is in
years and variance is an annualized variance rate.
"""

import math
from collections import Counter

import numpy as np
from scipy.linalg import solve_banded


def calendar_call_snapshots(
    spot,
    strike,
    maturity,
    variance,
    rate,
    q,
    dates,
    *,
    space_nodes=601,
    time_steps=960,
    log_half_width=1.8,
):
    """Independent banded CN snapshots; preserve absolute coefficient times.

    This extends the independently transcribed RB-F04 solver, retaining its
    support statuses, damping and finite-domain diagnostics. A solve is not
    labeled exact or converged: selected refinements measure its uncertainty.
    """
    result = pde_call(
        spot,
        [strike],
        maturity,
        variance,
        rate,
        q,
        space_nodes,
        time_steps,
        log_half_width,
        snapshot_dates=dates,
    )
    return {
        **result,
        "values": result["snapshots"][:, 0, :],
        "spots": result["grid"]["spots"],
        "dates": np.asarray(dates),
    }


def selected_call_refinement(
    parameters,
    surface,
    *,
    model,
    date,
    spot,
    state,
    space_nodes=601,
    time_steps=960,
    log_half_width=1.8,
    upper=250.0,
    spot_bump=0.02,
    state_bump=None,
    quadrature_limit=None,
):
    """Measure independent price/CS/Ctheta refinement at one selected state.

    CF cutoff is doubled; local space, time and domain are refined separately.
    CRN is irrelevant for deterministic references. Derivatives use centered
    three-width bumps and their finite-width changes are retained separately.
    This is a measured comparison, not a rigorous truncation-error bound.
    """
    from dataclasses import asdict, is_dataclass

    from scipy.interpolate import CubicSpline

    p = asdict(parameters) if is_dataclass(parameters) else dict(parameters)
    state_bump = (0.0001 if model == "heston" else 0.001) if state_bump is None else state_bump
    if model not in {"heston", "local"} or date < 0 or date >= 1.25 or state <= 2 * state_bump:
        raise ValueError("selected reference needs supported date/model/interior state")
    integration_receipts = []
    price_unit_errors = {}

    def calculate(s, v, level):
        if model == "heston":
            current = {**p, "spot": float(s), "v0": float(v)}
            receipt = independent_heston_call(
                [100.0],
                1.25 - date,
                current,
                upper=upper * (2 if level else 1),
                quadrature_limit=(1600 if level == 2 else 800)
                if quadrature_limit is None
                else quadrature_limit,
                epsabs=1e-13 if level == 2 else 1e-12,
                epsrel=1e-12 if level == 2 else 1e-11,
                return_receipt=True,
            )
            integration_receipts.append(
                {"level": level, "spot": float(s), "state": float(v), **receipt}
            )
            price_unit_errors[(level, s, v)] = float(receipt["price_unit_error"][0])
            return float(receipt["price"][0])
        if surface is None:
            raise ValueError("local reference requires a calendar surface")

        def coefficient(t, ss):
            raw = surface.evaluate(t, ss)
            return {**raw, "variance": np.asarray(raw["variance"]) * v}

        nodes = (2 * space_nodes - 1) if level == 1 else space_nodes
        steps = (2 * time_steps) if level == 2 else time_steps
        width = log_half_width * 1.25 if level == 3 else log_half_width
        result = calendar_call_snapshots(
            p["spot"],
            100.0,
            1.25,
            coefficient,
            p["rate"],
            p["dividend_yield"],
            [date],
            space_nodes=nodes,
            time_steps=steps,
            log_half_width=width,
        )
        if not result["supported"]:
            return np.nan
        return float(CubicSpline(np.log(result["spots"]), result["values"][0])(math.log(s)))

    levels = range(3 if model == "heston" else 4)
    prices, ds, dv, derivative_widths = [], [], [], []
    integration_derivative_errors = []
    for level in levels:
        prices.append(calculate(spot, state, level))
        spot_derivatives, state_derivatives = [], []
        derivative_errors = []
        for width in [1.0, 0.5, 2.0]:
            hs, hv = spot_bump * width, state_bump * width
            spot_derivatives.append(
                (calculate(spot + hs, state, level) - calculate(spot - hs, state, level)) / (2 * hs)
            )
            state_derivatives.append(
                (calculate(spot, state + hv, level) - calculate(spot, state - hv, level)) / (2 * hv)
            )
            derivative_errors.append(
                [
                    (
                        price_unit_errors.get((level, spot + hs, state), 0.0)
                        + price_unit_errors.get((level, spot - hs, state), 0.0)
                    )
                    / (2 * hs),
                    (
                        price_unit_errors.get((level, spot, state + hv), 0.0)
                        + price_unit_errors.get((level, spot, state - hv), 0.0)
                    )
                    / (2 * hv),
                ]
            )
        ds.append(spot_derivatives[1])
        dv.append(state_derivatives[1])
        derivative_widths.append([spot_derivatives, state_derivatives])
        integration_derivative_errors.append(derivative_errors)
    prices, ds, dv, widths = map(np.asarray, (prices, ds, dv, derivative_widths))
    finite = np.all(np.isfinite(prices)) and np.all(np.isfinite(widths))
    return {
        "status": "measured" if finite else "unknown",
        "model": model,
        "price": prices[-1],
        "spot_derivative": ds[-1],
        "state_derivative": dv[-1],
        "price_error": float(np.max(np.abs(prices - prices[0]))),
        "spot_derivative_error": float(np.max(np.abs(ds - ds[0]))),
        "state_derivative_error": float(np.max(np.abs(dv - dv[0]))),
        "prices": prices,
        "spot_derivatives": ds,
        "state_derivatives": dv,
        "three_width_derivatives": widths,
        "finite_width_errors": np.max(np.abs(widths - widths[:, :, [1]]), axis=(0, 2)),
        "integration_receipts": integration_receipts,
        "price_unit_error": max(price_unit_errors.values(), default=0.0),
        "integration_derivative_error": np.max(integration_derivative_errors, axis=(0, 1)),
        "refinements": ["cutoff", "adaptive_quadrature"]
        if model == "heston"
        else ["space", "time", "domain"],
    }


def direct_conditional_asian(
    parameters,
    surface,
    *,
    model,
    calendar_times,
    fixing_indices,
    spot,
    state,
    memory_sum,
    memory_count,
    seed,
    n_paths,
    spot_bump=0.02,
    state_bump=None,
):
    """Independent direct-payoff MC and CRN central bumps, without CE/control.

    Drivers are locally seeded and unrelated to the cache teacher. This own
    implementation uses the approved adapted log-stock / positive implicit-CIR
    scheme. It retains individual payoff/Greek samples and the original N.
    The caller measures scheme bias by a separate finer calendar/seed receipt.
    """
    from dataclasses import asdict, is_dataclass

    p = asdict(parameters) if is_dataclass(parameters) else dict(parameters)
    times = np.asarray(calendar_times, float)
    fixing_indices = np.asarray(fixing_indices)
    if (
        model not in {"heston", "local"}
        or n_paths < 2
        or times.ndim != 1
        or len(times) < 2
        or np.any(np.diff(times) <= 0)
        or times[0] < 0
        or abs(times[-1] - 1.0) > 1e-12
        or memory_count + len(fixing_indices) != 12
        or fixing_indices.dtype.kind not in "iu"
        or np.any(fixing_indices < 1)
        or np.any(fixing_indices >= len(times))
    ):
        raise ValueError(
            "direct reference needs exact monthly fixing indices and terminal calendar"
        )
    if not np.allclose(
        times[fixing_indices], np.arange(memory_count + 1, 13) / 12, atol=1e-12, rtol=0
    ):
        raise ValueError("monthly claim fixing dates must be preserved")
    state_bump = (0.0001 if model == "heston" else 0.001) if state_bump is None else state_bump
    if min(spot - 2 * spot_bump, state - 2 * state_bump) <= 0:
        raise ValueError("central bumps require positive interior spot/state")
    fixing_set = set(fixing_indices.tolist())

    def payoff(s, v):
        # Restart the local RNG for each bump: identical independent increments,
        # O(N) storage, and no mutation of caller/global RNG state.
        rng = np.random.default_rng(seed)
        stocks = np.full(n_paths, s, float)
        variances = np.full(n_paths, v, float)
        sums = np.full(n_paths, memory_sum, float)
        for i, dt in enumerate(np.diff(times)):
            noise = rng.standard_normal((n_paths, 2))
            zs, zp = noise[:, 0], noise[:, 1]
            if model == "heston":
                var = variances.copy()
                if p["xi"] == 0:
                    variances = p["theta"] + (var - p["theta"]) * math.exp(-p["kappa"] * dt)
                else:
                    zv = p["rho"] * zs + math.sqrt(1 - p["rho"] ** 2) * zp
                    a = (4 * p["kappa"] * p["theta"] - p["xi"] ** 2) / 8
                    if a <= 0:
                        raise ValueError(
                            "positive CIR reference requires 4 kappa theta > xi squared"
                        )
                    u = np.sqrt(var) + 0.5 * p["xi"] * math.sqrt(dt) * zv
                    d = 1 + 0.5 * p["kappa"] * dt
                    radical = np.sqrt(u * u + 4 * d * a * dt)
                    y = np.empty_like(u)
                    nonnegative = u >= 0
                    y[nonnegative] = (u[nonnegative] + radical[nonnegative]) / (2 * d)
                    y[~nonnegative] = 2 * a * dt / (radical[~nonnegative] - u[~nonnegative])
                    variances = y * y
            else:
                coefficient = surface.evaluate((times[i] + times[i + 1]) / 2, stocks)
                status = np.asarray(coefficient["status"]).astype(str)
                if np.any(np.char.startswith(status, "unsupported")):
                    return np.full(n_paths, np.nan)
                var = v * np.asarray(coefficient["variance"])
            if np.any(~np.isfinite(var)) or np.any(var < 0):
                return np.full(n_paths, np.nan)
            stocks *= np.exp(
                (p["rate"] - p["dividend_yield"] - 0.5 * var) * dt + np.sqrt(var * dt) * zs
            )
            if i + 1 in fixing_set:
                sums += stocks
        return math.exp(-p["rate"] * (1 - times[0])) * np.maximum(sums / 12 - 100.0, 0.0)

    values = payoff(spot, state)
    widths = []
    for w in [1.0, 0.5, 2.0]:
        hs, hv = spot_bump * w, state_bump * w
        ds = (payoff(spot + hs, state) - payoff(spot - hs, state)) / (2 * hs)
        dv = (payoff(spot, state + hv) - payoff(spot, state - hv)) / (2 * hv)
        widths.append(np.stack([ds, dv], axis=1))
    widths = np.asarray(widths)
    samples = np.column_stack([values, widths[1]])
    return {
        "status": "measured" if np.all(np.isfinite(samples)) else "unknown",
        "samples": samples,
        "mean": samples.mean(axis=0),
        "standard_errors": samples.std(axis=0, ddof=1) / math.sqrt(n_paths),
        "covariance": np.cov(samples, rowvar=False) / n_paths,
        "N": n_paths,
        "original_path_count": n_paths,
        "seed": seed,
        "model": model,
        "three_width_greek_means": widths.mean(axis=1),
        "scheme_error": "unmeasured_requires_independent_refinement",
    }


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
    snapshot_dates=None,
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
    T / time_steps
    values = np.maximum(spots[:, None] - strikes[None, :], 0.0)
    statuses = Counter()
    evaluation_times = []
    negative_operator_coefficients = 0
    tau = 0.0
    snapshot_dates = np.array([0.0] if snapshot_dates is None else snapshot_dates, dtype=float)
    if snapshot_dates.ndim != 1 or np.any(snapshot_dates < 0) or np.any(snapshot_dates >= T):
        raise ValueError("snapshots require exact calendar dates in [0,T)")
    saved = {}
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

    backward_nodes = np.unique(np.r_[np.linspace(0.0, T, time_steps + 1), T - snapshot_dates])
    for index, interval in enumerate(np.diff(backward_nodes)):
        if failure is not None:
            break
        increments = (interval / 2, interval / 2) if index == 0 else (interval,)
        weight = 1.0 if index == 0 else 0.5
        for increment in increments:
            failure = step(tau + increment, increment, weight)
            if failure is not None:
                break
            tau += increment
        if failure is not None:
            break
        for date in snapshot_dates:
            if abs(T - tau - date) < 1e-12:
                saved[float(date)] = values.T.copy()

    price = (
        np.array([np.interp(math.log(spot), x, row) for row in values.T])
        if failure is None
        else np.full(strikes.shape, np.nan)
    )
    return {
        "snapshots": np.stack(
            [saved.get(float(t), np.full_like(values.T, np.nan)) for t in snapshot_dates]
        ),
        "snapshot_dates": snapshot_dates,
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


def independent_heston_call(
    strikes,
    T,
    parameters,
    upper=250.0,
    *,
    quadrature_limit=800,
    epsabs=1e-12,
    epsrel=1e-11,
    return_receipt=False,
):
    """Price calls using two own-CF Gil-Pelaez probability integrals.

    Parameters may be a mapping or an object with spot, rate, dividend_yield,
    v0, kappa, theta, xi and rho attributes. The formula is independently
    transcribed from the existing research reference in
    scripts/build_stochastic_volatility_reference.py, without importing it
    or any hullkit transform. The finite integration upper bound is explicit;
    callers compare separate bounds to diagnose truncation.

    xi=0 uses the exact integrated deterministic variance in the own CF.
    The zero-integrated-variance case returns discounted intrinsic value.
    ``return_receipt`` preserves each full-output integral's error, convergence
    message, evaluation count and used subinterval data. Nonconverged prices
    remain NaN in the ordinary result; finite raw estimates are saved separately.
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
        or not isinstance(quadrature_limit, (int, np.integer))
        or isinstance(quadrature_limit, bool)
        or quadrature_limit < 1
        or not np.isfinite(epsabs + epsrel)
        or epsabs <= 0
        or epsrel <= 0
    ):
        raise ValueError(
            "finite positive market/integration inputs and valid Heston parameters required"
        )
    discount_stock = p["spot"] * math.exp(-p["dividend_yield"] * T)
    discount = math.exp(-p["rate"] * T)
    if _integrated_variance(p, T) == 0:
        prices = np.maximum(discount_stock - strikes * discount, 0.0)
        if not return_receipt:
            return prices
        return {
            "price": prices,
            "raw_prices": prices.copy(),
            "status": "converged",
            "price_unit_error": np.zeros_like(prices),
            "integration_receipts": [[] for _ in strikes],
        }

    # E[S_T] is known analytically, including cases where the -i CF formula
    # itself has a removable singularity. It normalizes the stock measure.
    stock_moment = p["spot"] * math.exp((p["rate"] - p["dividend_yield"]) * T)
    settings = {"limit": quadrature_limit, "epsabs": epsabs, "epsrel": epsrel}
    prices, raw_prices, errors, receipts = [], [], [], []
    for strike in strikes:
        log_k = math.log(strike)

        def stock_probability_integrand(u, log_k=log_k):
            return (
                np.exp(-1j * u * log_k) * _log_price_cf(u - 1j, T, p) / (1j * u * stock_moment)
            ).real

        def money_probability_integrand(u, log_k=log_k):
            return (np.exp(-1j * u * log_k) * _log_price_cf(u, T, p) / (1j * u)).real

        integrals = []
        for integrand in [stock_probability_integrand, money_probability_integrand]:
            result = quad(integrand, 0.0, upper, full_output=1, **settings)
            integral, error, info = result[:3]
            message = result[3] if len(result) > 3 else ""
            last = int(info["last"])
            integrals.append(
                {
                    "value": float(integral),
                    "absolute_error": float(error),
                    "status": "converged"
                    if not message and np.isfinite(integral + error)
                    else "nonconverged",
                    "message": message,
                    "neval": int(info["neval"]),
                    "subinterval_count": last,
                    "subintervals": np.column_stack(
                        [info[key][:last] for key in ["alist", "blist", "rlist", "elist"]]
                    ),
                    "quadrature_limit": quadrature_limit,
                    "epsabs": epsabs,
                    "epsrel": epsrel,
                    "upper": upper,
                }
            )
        p1, p2 = [0.5 + result["value"] / math.pi for result in integrals]
        raw = discount_stock * p1 - strike * discount * p2
        raw_prices.append(raw)
        errors.append(
            (
                discount_stock * integrals[0]["absolute_error"]
                + strike * discount * integrals[1]["absolute_error"]
            )
            / math.pi
        )
        converged = all(result["status"] == "converged" for result in integrals) and np.isfinite(
            raw
        )
        prices.append(raw if converged else np.nan)
        receipts.append(integrals)
    prices = np.asarray(prices)
    if not return_receipt:
        return prices
    return {
        "price": prices,
        "raw_prices": np.asarray(raw_prices),
        "price_unit_error": np.asarray(errors),
        "integration_receipts": receipts,
        "status": "converged" if np.all(np.isfinite(prices)) else "unknown",
    }
