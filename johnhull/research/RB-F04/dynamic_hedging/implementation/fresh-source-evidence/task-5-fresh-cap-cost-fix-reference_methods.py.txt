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
    wall_cap_seconds=None,
    deadline_wall=None,
):
    """Measure independent price/CS/Ctheta refinement at one selected state.

    CF cutoff is doubled; local space, time and domain are refined separately.
    CRN is irrelevant for deterministic references. Derivatives use centered
    three-width bumps and their finite-width changes are retained separately.
    This is a measured comparison, not a rigorous truncation-error bound.
    """
    import time
    from dataclasses import asdict, is_dataclass

    from scipy.interpolate import CubicSpline

    started = time.perf_counter()
    deadline = _deadline(wall_cap_seconds, started, deadline_wall=deadline_wall)
    p = asdict(parameters) if is_dataclass(parameters) else dict(parameters)
    state_bump = (0.0001 if model == "heston" else 0.001) if state_bump is None else state_bump
    if model not in {"heston", "local"} or date < 0 or date >= 1.25 or state <= 2 * state_bump:
        raise ValueError("selected reference needs supported date/model/interior state")
    integration_receipts = []
    pde_receipts = []
    price_unit_errors = {}

    def calculate(s, v, level):
        if _expired(deadline):
            return np.nan
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
        pde_receipts.append({"level": level, "spot": float(s), "state": float(v), **result})
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
        "pde_receipts": pde_receipts,
        "inputs": {
            "model": model,
            "date": date,
            "spot": spot,
            "state": state,
            "spot_bump": spot_bump,
            "state_bump": state_bump,
        },
        "cap_evidence": _table_cap_receipt(
            wall_cap_seconds,
            started,
            len(levels) * 13,
            len(integration_receipts) if model == "heston" else len(pde_receipts),
            deadline_wall=deadline,
        ),
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
    normals=None,
):
    """Independent direct-payoff MC and three-width CRN central state bumps.

    The legacy mean/sample interface and step-major seeded driver remain.
    New diagnostics preserve supported raw paths without certifying a finite
    subset when any original path is unsupported. This is not a precision gate.
    """
    state_bump = (0.0001 if model == "heston" else 0.001) if state_bump is None else state_bump
    if min(spot - 2 * spot_bump, state - 2 * state_bump) <= 0:
        raise ValueError("central bumps require positive interior spot/state")
    args = dict(
        model=model,
        calendar_times=calendar_times,
        fixing_indices=fixing_indices,
        memory_sum=memory_sum,
        memory_count=memory_count,
        seed=seed,
        n_paths=n_paths,
        normals=normals,
    )
    query = [(spot, state)]
    for bump, axis in [(spot_bump, 0), (state_bump, 1)]:
        for w in [1.0, 0.5, 2.0]:
            for sign in [1, -1]:
                query.append(
                    (spot + sign * bump * w, state)
                    if axis == 0
                    else (spot, state + sign * bump * w)
                )
    raw = [direct_asian_price(parameters, surface, spot=s, state=v, **args) for s, v in query]
    payoffs = np.asarray([v["samples"] for v in raw])
    widths = np.stack(
        [
            np.column_stack(
                [
                    (payoffs[1 + 2 * j] - payoffs[2 + 2 * j]) / (2 * spot_bump * w),
                    (payoffs[7 + 2 * j] - payoffs[8 + 2 * j]) / (2 * state_bump * w),
                ]
            )
            for j, w in enumerate([1.0, 0.5, 2.0])
        ]
    )
    samples = np.column_stack([payoffs[0], widths[1]])
    return {
        **_sample_summary(samples),
        "status": "measured" if np.all(np.isfinite(samples)) else "unknown",
        "samples": samples,
        "payoff_samples": payoffs,
        "width_position_samples": widths,
        "N": n_paths,
        "original_path_count": n_paths,
        "seed": seed,
        "model": model,
        "path_status": np.asarray([v["path_status"] for v in raw]),
        "first_failure_date": np.asarray([v["first_failure_date"] for v in raw]),
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


def _parameters(parameters):
    from dataclasses import asdict, is_dataclass

    return asdict(parameters) if is_dataclass(parameters) else dict(parameters)


def _sample_summary(samples, *, exact=False):
    """Whole-original-N summaries; finite-only output is explicitly descriptive."""
    a = np.asarray(samples, float)
    n = len(a)
    all_finite = bool(np.all(np.isfinite(a)))
    mean = a.mean(axis=0)
    se = a.std(axis=0, ddof=1) / math.sqrt(n) if n > 1 else np.full_like(mean, np.nan)
    covariance = np.atleast_2d(np.cov(a, rowvar=False)) / n if n > 1 else np.full((1, 1), np.nan)
    valid = np.isfinite(a) if a.ndim == 1 else np.all(np.isfinite(a), axis=1)
    finite = a[valid]
    descriptive = {
        "finite_path_count": int(np.sum(valid)),
        "mean": finite.mean(axis=0) if len(finite) else np.full_like(mean, np.nan),
        "label": "descriptive_only_not_financial_qualification",
    }
    price = a if a.ndim == 1 else a[:, 0]
    underresolved = all_finite and not exact and np.all(price == price[0])
    status = (
        "exact_input_identity"
        if exact
        else (
            "unknown_support"
            if not all_finite
            else "unknown_underresolved"
            if underresolved
            else "measured"
        )
    )
    return {
        "mean": mean,
        "standard_errors": se,
        "covariance": covariance,
        "statistical_status": status,
        "descriptive_only": descriptive,
    }


def direct_asian_price(
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
    normals=None,
):
    """Own direct arithmetic-payoff MC, preserving every original path status.

    Supplied independent normals have shape (N, steps, 2). Otherwise the legacy
    step-major local RNG is used. Unsupported local paths retain their first
    failure and NaN payoff; supported paths survive only as raw diagnostics.
    No pathwise or sample-precision claim follows from successful simulation.
    """
    p = _parameters(parameters)
    times = np.asarray(calendar_times, float)
    indices = np.asarray(fixing_indices, dtype=int)
    if (
        model not in {"heston", "local"}
        or n_paths < 2
        or times.ndim != 1
        or len(times) < 2
        or np.any(np.diff(times) <= 0)
        or times[0] < 0
        or abs(times[-1] - 1) > 1e-12
        or memory_count + len(indices) != 12
        or np.any(indices < 1)
        or np.any(indices >= len(times))
        or spot <= 0
        or state <= 0
        or memory_sum < 0
    ):
        raise ValueError("direct reference needs positive state and exact monthly calendar")
    if not np.allclose(times[indices], np.arange(memory_count + 1, 13) / 12, atol=1e-12, rtol=0):
        raise ValueError("monthly claim fixing dates must be preserved")
    if model == "local" and surface is None:
        raise ValueError("local reference requires measured calendar surface")
    if model == "heston" and p["xi"] and 4 * p["kappa"] * p["theta"] <= p["xi"] ** 2:
        raise ValueError("positive CIR reference requires 4 kappa theta > xi squared")
    if normals is not None:
        normals = np.asarray(normals, float)
        if normals.shape != (n_paths, len(times) - 1, 2) or not np.all(np.isfinite(normals)):
            raise ValueError("normal driver needs exact original path/calendar shape")
    rng = np.random.default_rng(seed)
    stocks = np.full(n_paths, spot, float)
    variances = np.full(n_paths, state, float)
    sums = np.full(n_paths, memory_sum, float)
    status = np.full(n_paths, "supported", dtype="U96")
    first = np.full(n_paths, np.nan)
    valid = np.ones(n_paths, bool)
    fixing_set = set(indices.tolist())
    for i, dt in enumerate(np.diff(times)):
        noise = rng.standard_normal((n_paths, 2)) if normals is None else normals[:, i, :]
        zs, zp = noise[:, 0], noise[:, 1]
        if model == "heston":
            var = variances.copy()
            if p["xi"] == 0:
                variances = p["theta"] + (var - p["theta"]) * math.exp(-p["kappa"] * dt)
            else:
                zv = p["rho"] * zs + math.sqrt(1 - p["rho"] ** 2) * zp
                a = (4 * p["kappa"] * p["theta"] - p["xi"] ** 2) / 8
                u = np.sqrt(var) + 0.5 * p["xi"] * math.sqrt(dt) * zv
                d = 1 + 0.5 * p["kappa"] * dt
                radical = np.sqrt(u * u + 4 * d * a * dt)
                y = np.empty_like(u)
                pos = u >= 0
                y[pos] = (u[pos] + radical[pos]) / (2 * d)
                y[~pos] = 2 * a * dt / (radical[~pos] - u[~pos])
                variances = y * y
        else:
            raw = surface.evaluate((times[i] + times[i + 1]) / 2, stocks)
            labels = np.broadcast_to(np.asarray(raw["status"]).astype(str), stocks.shape)
            unsupported = valid & np.char.startswith(labels, "unsupported")
            status[unsupported] = labels[unsupported]
            first[unsupported] = (times[i] + times[i + 1]) / 2
            valid[unsupported] = False
            var = state * np.broadcast_to(np.asarray(raw["variance"], float), stocks.shape)
        bad = valid & ((~np.isfinite(var)) | (var < 0))
        status[bad] = "unsupported_coefficient"
        first[bad] = (times[i] + times[i + 1]) / 2
        valid[bad] = False
        with np.errstate(over="ignore", invalid="ignore"):
            stocks[valid] *= np.exp(
                (p["rate"] - p["dividend_yield"] - 0.5 * var[valid]) * dt
                + np.sqrt(var[valid] * dt) * zs[valid]
            )
        bad = valid & ((~np.isfinite(stocks)) | (stocks <= 0))
        status[bad] = "unsupported_nonfinite_stock"
        first[bad] = times[i + 1]
        valid[bad] = False
        stocks[~valid] = np.nan
        if i + 1 in fixing_set:
            sums[valid] += stocks[valid]
    values = np.full(n_paths, np.nan)
    values[valid] = math.exp(-p["rate"] * (1 - times[0])) * np.maximum(sums[valid] / 12 - 100, 0)
    summary = _sample_summary(values)
    return {
        **summary,
        "standard_error": float(summary["standard_errors"]),
        "samples": values,
        "path_status": status,
        "first_failure_date": first,
        "supported_path_mask": valid,
        "original_path_count": n_paths,
        "N": n_paths,
        "seed": int(seed),
        "model": model,
        "calendar_times": times,
        "fixing_indices": indices,
        "input_state": {
            "spot": spot,
            "state": state,
            "memory_sum": memory_sum,
            "memory_count": memory_count,
        },
    }


def coarsen_normals(fine):
    """Aggregate adjacent fine Brownian increments without redrawing paths."""
    fine = np.asarray(fine, float)
    if fine.ndim != 3 or fine.shape[2] != 2 or fine.shape[1] % 2:
        raise ValueError("paired driver requires an even fine step count and two coordinates")
    return fine.reshape(fine.shape[0], fine.shape[1] // 2, 2, 2).sum(axis=2) / math.sqrt(2)


def _field_binding(surface):
    """Bind production field arrays; generic fixture classes remain explicit."""
    if surface is None:
        return None, None
    import hashlib

    descriptor = {"class": f"{type(surface).__module__}.{type(surface).__qualname__}"}
    signature = {"class": descriptor["class"]}
    for key in ("times", "z_nodes", "values", "wing_boundaries", "support_mask"):
        if hasattr(surface, key):
            value = getattr(surface, key)
            descriptor[key] = value
            if value is None:
                signature[key] = None
            else:
                array = np.asarray(value)
                signature[key] = {
                    "shape": list(array.shape),
                    "dtype": str(array.dtype),
                    "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
                }
    if hasattr(surface, "parameters"):
        signature["parameters"] = _parameters(surface.parameters)
        descriptor["parameters"] = signature["parameters"]
    return descriptor, signature


def fit_independent_quote(state_nodes, prices, quote, *, model, spot, query_id=None):
    """Enumerate the complete physical-state cubic quote curve using PPoly.solve.

    This independently fits the call curve over the ORIGINAL call domain before
    Asian patch restrictions. Raw solve output (including continuum NaNs) and
    all distinct roots survive. A unique root is not a precision certificate.
    The operational kappa bound uses a one-cent quote error, never bump width.
    """
    from scipy.interpolate import CubicSpline

    bounds = [1e-5, 0.5] if model == "heston" else [0.25, 4.0] if model == "local" else None
    nodes = np.asarray(state_nodes, float)
    values = np.asarray(prices, float)
    if (
        bounds is None
        or nodes.ndim != 1
        or len(nodes) < 4
        or values.shape != nodes.shape
        or np.any(np.diff(nodes) <= 0)
        or nodes[0] != bounds[0]
        or nodes[-1] != bounds[1]
    ):
        raise ValueError("independent quote fit needs the full original call state domain")
    result = {
        "query_id": query_id,
        "spot": float(spot),
        "quote": float(quote),
        "full_domain_bounds": bounds,
        "state_nodes": nodes,
        "call_prices": values,
        "full_domain_roots": np.array([], float),
        "raw_roots": np.array([], float),
        "state": np.nan,
        "residual": np.nan,
        "Ctheta": np.nan,
        "condition_number": np.nan,
        "solver_status": "unsupported_reference",
        "operational_status": "unknown",
        "reason": "nonfinite full-domain call reference",
    }
    if not np.all(np.isfinite(values)) or not np.isfinite(quote):
        return result
    curve = CubicSpline(nodes, values, extrapolate=False)
    raw = np.asarray(curve.solve(float(quote), extrapolate=False), float)
    roots = []
    for root in np.sort(raw[np.isfinite(raw)]):
        if bounds[0] <= root <= bounds[1] and not any(abs(root - r) <= 1e-10 for r in roots):
            roots.append(float(root))
    critical = np.asarray(curve.derivative().solve(0.0, extrapolate=False))
    partition = np.unique(np.r_[nodes, critical[np.isfinite(critical)]])
    brackets = []
    bracket_residuals = []
    for root in roots:
        at = np.flatnonzero(np.abs(partition - root) <= 1e-10)
        if len(at):
            left = right = root
        else:
            right_index = int(np.searchsorted(partition, root))
            left, right = partition[right_index - 1], partition[right_index]
        brackets.append([left, right])
        bracket_residuals.append([float(curve(left) - quote), float(curve(right) - quote)])
    result.update(
        raw_roots=raw,
        full_domain_roots=np.asarray(roots),
        spline_coefficients=curve.c.copy(),
        critical_points=critical,
        root_brackets=np.asarray(brackets, float).reshape(-1, 2),
        bracket_residuals=np.asarray(bracket_residuals, float).reshape(-1, 2),
    )
    if np.any(np.isnan(raw)) or len(roots) > 1:
        result.update(solver_status="nonunique", reason="multiple roots or constant quote interval")
    elif not roots:
        result.update(solver_status="no_root", reason="no root in the full original call domain")
    else:
        state = roots[0]
        derivative = float(curve.derivative()(state))
        scale = 0.04 if model == "heston" else 1.0
        condition = 0.01 / (abs(derivative) * scale) if derivative else np.inf
        result.update(
            state=state,
            residual=float(curve(state) - quote),
            Ctheta=derivative,
            condition_number=condition,
            solver_status="unique_root",
            operational_status="within_envelope" if condition <= 0.25 else "ill_conditioned",
            reason="measured root; precision is unchecked"
            if condition <= 0.25
            else "original one-cent quote conditioning exceeds 0.25",
        )
    return result


def independent_call_table(
    parameters,
    surface,
    *,
    model,
    dates,
    query_spots,
    state_nodes,
    controls,
    wall_cap_seconds=None,
    deadline_wall=None,
):
    """Compute full-call-domain independent CF/PDE tables and raw refinements.

    Heston uses three quadrature/cutoff levels. Local uses separate space/time/
    domain refinements with absolute calendar coefficients. Interpolation never
    extrapolates query spots. Controls and all raw integration/PDE evidence are
    retained; numerical success is distinct from financial qualification.
    """
    import time

    from scipy.interpolate import CubicSpline

    started = time.perf_counter()
    deadline = _deadline(wall_cap_seconds, started, deadline_wall=deadline_wall)
    p = _parameters(parameters)
    surface_descriptor, surface_signature = _field_binding(surface)
    dates, spots, nodes = map(lambda x: np.asarray(x, float), (dates, query_spots, state_nodes))
    bounds = [1e-5, 0.5] if model == "heston" else [0.25, 4.0] if model == "local" else None
    if (
        bounds is None
        or len(nodes) < 4
        or nodes[0] != bounds[0]
        or nodes[-1] != bounds[1]
        or np.any(np.diff(nodes) <= 0)
        or np.any((dates < 0) | (dates >= 1.25))
        or len(dates) == 0
        or len(spots) == 0
        or np.any(spots <= 0)
    ):
        raise ValueError("table requires complete original call domain and positive query spots")
    if model == "local" and surface is None:
        raise ValueError("local call table requires calendar surface")
    levels = 3 if model == "heston" else 4
    prices = np.full((levels, len(dates), len(spots), len(nodes)), np.nan)
    errors = np.full_like(prices, np.nan)
    integration, pdes, expenses = [], [], []
    settings = dict(controls)
    for level in range(levels):
        if _expired(deadline):
            break
        wall, cpu = time.perf_counter(), time.process_time()
        for j, state in enumerate(nodes):
            if _expired(deadline):
                break
            if model == "heston":
                for d, date in enumerate(dates):
                    for s, spot in enumerate(spots):
                        if _expired(deadline):
                            break
                        receipt = independent_heston_call(
                            [100.0],
                            1.25 - date,
                            {**p, "spot": float(spot), "v0": float(state)},
                            upper=settings.get("upper", 250.0) * (2 if level else 1),
                            quadrature_limit=settings.get(
                                "quadrature_limit", 1600 if level == 2 else 800
                            ),
                            epsabs=settings.get("epsabs", 1e-13 if level == 2 else 1e-12),
                            epsrel=settings.get("epsrel", 1e-12 if level == 2 else 1e-11),
                            return_receipt=True,
                        )
                        prices[level, d, s, j] = receipt["price"][0]
                        errors[level, d, s, j] = receipt["price_unit_error"][0]
                        integration.append(
                            {
                                "level": level,
                                "date_index": d,
                                "spot_index": s,
                                "state_index": j,
                                **receipt,
                            }
                        )
            else:

                def variance(t, ss, state=state):
                    raw = surface.evaluate(t, ss)
                    return {**raw, "variance": np.asarray(raw["variance"]) * state}

                base_nodes = settings.get("space_nodes", 601)
                result = calendar_call_snapshots(
                    p["spot"],
                    100.0,
                    1.25,
                    variance,
                    p["rate"],
                    p["dividend_yield"],
                    dates,
                    space_nodes=2 * base_nodes - 1 if level == 1 else base_nodes,
                    time_steps=settings.get("time_steps", 960) * (2 if level == 2 else 1),
                    log_half_width=settings.get("log_half_width", 1.8)
                    * (1.25 if level == 3 else 1),
                )
                pdes.append({"level": level, "state_index": j, **result})
                if result["supported"]:
                    log_grid = np.log(result["spots"])
                    inside = (spots >= result["spots"][0]) & (spots <= result["spots"][-1])
                    for d in range(len(dates)):
                        curve = CubicSpline(log_grid, result["values"][d], extrapolate=False)
                        prices[level, d, inside, j] = curve(np.log(spots[inside]))
        expenses.append(
            {
                "job_id": f"independent-call-level-{level}",
                "scope": "independent_call_reference",
                "level": level,
                **_timing(wall, cpu, deadline),
                "path_steps": 0,
                "original_path_count": 0,
            }
        )
    return {
        "schema": "rb-f04-independent-call-table-v1",
        "surface_descriptor": surface_descriptor,
        "surface_signature": surface_signature,
        "model": model,
        "parameters": p,
        "dates": dates,
        "query_spots": spots,
        "state_nodes": nodes,
        "original_bounds": bounds,
        "controls": settings,
        "prices": prices,
        "price_unit_errors": errors,
        "integration_receipts": integration,
        "pde_receipts": pdes,
        "expenses": expenses,
        "refinement_kinds": ["base", "cutoff", "quadrature"]
        if model == "heston"
        else ["base", "space", "time", "domain"],
        "financial_qualification": "unchecked",
        "cap_evidence": _table_cap_receipt(
            wall_cap_seconds,
            started,
            prices.size,
            len(integration) if model == "heston" else len(pdes) * len(dates) * len(spots),
            deadline_wall=deadline,
        ),
    }


def _calendar(date, count, level):
    if abs(date - count / 12) > 1e-12 or level % 12:
        raise ValueError("paired monthly calendar requires count/12 and level multiple of 12")
    start = round(date * level)
    times = np.arange(start, level + 1, dtype=float) / level
    fixing = np.asarray([round(j * level / 12) - start for j in range(count + 1, 13)], int)
    return times, fixing


def _normal_digest(normals):
    import hashlib

    h = hashlib.sha256()
    for first in range(0, len(normals), 128):
        h.update(normals[first : first + 128].tobytes())
    return h.hexdigest()


def _driver_chunks(n_paths, fine_steps, seed, chunk_paths, supplied=None, deadline=None):
    """Yield bounded paired drivers with explicit seed/path/query CRN mapping."""
    import time

    if chunk_paths < 2 or chunk_paths * fine_steps * 2 * 8 * 2 + 16 * 1024**2 > 256 * 1024**2:
        raise ValueError("driver chunk exceeds the 256 MiB paired-driver memory cap")
    if chunk_paths * fine_steps > 1_000_000_000:
        raise ValueError("driver subjob exceeds original one-billion path-step cap")
    if supplied is not None:
        supplied = np.asarray(supplied, float)
        if supplied.shape != (n_paths, fine_steps, 2) or supplied.nbytes > 128 * 1024**2:
            raise ValueError("supplied fine normals must match N/steps and bounded memory")
    for index, start in enumerate(range(0, n_paths, chunk_paths)):
        if deadline is not None and time.perf_counter() >= deadline:
            break
        stop = min(start + chunk_paths, n_paths)
        wall, cpu = time.perf_counter(), time.process_time()
        child = int(np.random.SeedSequence([int(seed), 7426, index]).generate_state(1)[0])
        fine = (
            np.random.default_rng(child).standard_normal((stop - start, fine_steps, 2))
            if supplied is None
            else supplied[start:stop]
        )
        coarse = coarsen_normals(fine)
        yield (
            start,
            stop,
            (coarse, fine),
            {
                "chunk_index": index,
                "path_range": [start, stop],
                "original_path_count": n_paths,
                "reserved_parent_seed": int(seed),
                "child_seed": child,
                "mapping": "SeedSequence[parent_seed,7426,chunk_index]; path-major; paired adjacent fine steps",
                "driver_source": "supplied" if supplied is not None else "reserved_local_rng",
                "fine_normal_sha256": _normal_digest(fine),
                "fine_shape": list(fine.shape),
                "coarse_shape": list(coarse.shape),
                "max_live_driver_bytes": int(fine.nbytes + 2 * coarse.nbytes),
                **_timing(wall, cpu, deadline),
            },
        )


def _blocks(samples):
    if len(samples) % 16:
        raise ValueError("reference covariance needs all original paths in 16 equal IID blocks")
    return np.asarray(samples).reshape(16, len(samples) // 16, *samples.shape[1:]).mean(axis=1)


def _oracle_arrays(payoffs, spot_bump, quote_bump):
    widths = np.stack(
        [
            np.column_stack(
                [
                    (payoffs[1 + 2 * j] - payoffs[2 + 2 * j]) / (2 * spot_bump * w),
                    (payoffs[7 + 2 * j] - payoffs[8 + 2 * j]) / (2 * quote_bump * w),
                ]
            )
            for j, w in enumerate([1.0, 0.5, 2.0])
        ]
    )
    return np.column_stack([payoffs[0], widths[1]]), widths


def _status_codes(values, labels):
    values = np.asarray(values).astype(str)
    encoded = np.zeros(values.shape, dtype=np.uint16)
    for label in np.unique(values):
        text = str(label)
        if text not in labels:
            if len(labels) >= 65536:
                raise ValueError("too many distinct original support reasons")
            labels.append(text)
        encoded[values == label] = labels.index(text)
    return encoded


def _timing(wall, cpu, deadline=None):
    import time

    stop, cpu_stop = time.perf_counter(), time.process_time()
    return {
        "clock": {"wall_start": wall, "wall_stop": stop, "cpu_start": cpu, "cpu_stop": cpu_stop},
        "wall_seconds": stop - wall,
        "cpu_seconds": cpu_stop - cpu,
        "deadline_wall": deadline,
        "overrun_seconds": max(0.0, stop - deadline) if deadline is not None else 0.0,
    }


def _deadline(wall_cap_seconds, started, *, deadline_wall=None):
    if wall_cap_seconds is None:
        if deadline_wall is not None:
            raise ValueError("absolute deadline requires an explicit effective wall budget")
        return None
    if not np.isfinite(wall_cap_seconds) or wall_cap_seconds < 0:
        raise ValueError("reference wall cap must be finite and nonnegative")
    if deadline_wall is not None and not np.isfinite(deadline_wall):
        raise ValueError("absolute wall deadline must be finite")
    return started + wall_cap_seconds if deadline_wall is None else deadline_wall


def _expired(deadline):
    import time

    return deadline is not None and time.perf_counter() >= deadline


def _table_cap_receipt(cap, started, planned, completed, *, deadline_wall=None):
    import time

    if cap is None:
        return None
    stop = time.perf_counter()
    elapsed = stop - started
    deadline = started + cap if deadline_wall is None else deadline_wall
    return {
        "cap_seconds": float(cap),
        "clock": {"wall_start": started, "wall_stop": stop},
        "budget_wall_start": deadline - cap,
        "deadline_wall": deadline,
        "wall_seconds": elapsed,
        "overrun_seconds": max(0.0, stop - deadline),
        "cap_reached": stop >= deadline,
        "planned_cells": planned,
        "completed_cells": completed,
        "unexecuted_cell_count": planned - completed,
        "boundary": "before each independent CF/PDE solve; no solver-internal hard cancellation",
        "financial_qualification": "unknown",
    }


def _cap_receipt(cap, started, statuses, labels, *, deadline_wall=None):
    import time

    if cap is None:
        return None
    stop = time.perf_counter()
    elapsed = stop - started
    deadline = started + cap if deadline_wall is None else deadline_wall
    remaining = np.zeros(statuses.shape[:-1], dtype=int)
    for label in ["unmeasured_cap", "unmeasured"]:
        if label in labels:
            remaining += np.count_nonzero(statuses == labels.index(label), axis=-1)
    return {
        "cap_seconds": float(cap),
        "clock": {"wall_start": started, "wall_stop": stop},
        "budget_wall_start": deadline - cap,
        "deadline_wall": deadline,
        "wall_seconds": elapsed,
        "overrun_seconds": max(0.0, stop - deadline),
        "cap_reached": stop >= deadline,
        "unexecuted_query_path_counts": remaining,
        "boundary": "checked before driver chunk and query job; no solver-internal hard cancellation",
        "financial_qualification": "unknown",
    }


def quote_positions_oracle(
    parameters,
    surface,
    *,
    model,
    date,
    spot,
    quote,
    memory_sum,
    memory_count,
    seed,
    n_paths,
    call_table,
    steps_per_year=1536,
    spot_bump=0.02,
    quote_bump=1e-4,
    normals=None,
    chunk_paths=4096,
    wall_cap_seconds=None,
    deadline_wall=None,
):
    """Independent S/Q re-fit direct-payoff oracle with paired raw refinements.

    All 13 original queries and paths remain. Per-query unique roots come from
    the full independent call curve; kappa failures remain operational unknown.
    Each query/chunk/level is a separately timed bounded job. Half-width Greeks
    are selected a priori; three-width covariance and 16 original blocks stay.
    """
    import time

    started = time.perf_counter()
    deadline = _deadline(wall_cap_seconds, started, deadline_wall=deadline_wall)
    p = _parameters(parameters)
    if steps_per_year % 24 or chunk_paths < 16 or chunk_paths % 16:
        raise ValueError("oracle needs fine paired monthly level and 16-aligned path chunks")
    if n_paths < 16 or n_paths % 16 or spot <= 2 * spot_bump or quote_bump <= 0 or spot_bump <= 0:
        raise ValueError("oracle needs positive bumps and original N divisible by 16")
    if model not in {"heston", "local"} or memory_count not in range(13):
        raise ValueError("oracle needs the original model and monthly memory count")
    if not 0 <= date <= 1 or abs(date - memory_count / 12) > 1e-12 or memory_sum < 0:
        raise ValueError("oracle preserves the original monthly claim calendar")
    query_ids = ["base"] + [
        f"{axis}{sign}.{width}"
        for axis in ["S", "Q"]
        for width in ["1", ".5", "2"]
        for sign in ["+", "-"]
    ]
    queries = [(spot, quote)]
    for axis, bump in [("S", spot_bump), ("Q", quote_bump)]:
        for width in [1.0, 0.5, 2.0]:
            for sign in [1, -1]:
                queries.append(
                    (spot + sign * bump * width, quote)
                    if axis == "S"
                    else (spot, quote + sign * bump * width)
                )
    levels = [steps_per_year // 2, steps_per_year]
    count = len(queries)
    payoff = np.full((2, count, n_paths), np.nan)
    status_labels = ["unmeasured_cap"]
    statuses = np.zeros((2, count, n_paths), dtype=np.uint16)
    first = np.full((2, count, n_paths), date)
    exact = memory_count == 12 or memory_sum >= 1200
    fits, expenses, drivers = [], [], []
    refinement = None
    refinement_status = {"status": "unmeasured", "reason": "reference not yet attempted"}
    curve_diagnostics = None
    if exact:
        refinement_status = {
            "status": "not_required_exact_input_identity",
            "reason": "linear_or_settled_claim",
        }
        # Input proof: positive future stock makes the payoff linear if A>=12K.
        # Settled payoffs do not require a model, call fit or RNG.
        remaining = np.arange(memory_count + 1, 13) / 12
        growth = np.sum(np.exp((p["rate"] - p["dividend_yield"]) * (remaining - date)))
        discount = math.exp(-p["rate"] * (1 - date))
        for j, (s, q) in enumerate(queries):
            value = discount * (memory_sum / 12 - 100 + s * growth / 12)
            if memory_count == 12:
                value = max(memory_sum / 12 - 100, 0.0)
            payoff[:, j, :] = value
            fits.append(
                {
                    "query_id": query_ids[j],
                    "spot": s,
                    "quote": q,
                    "solver_status": "not_required_exact_input_identity",
                    "operational_status": "exact_input_identity",
                    "reason": "linear_or_settled_claim",
                }
            )
        status_labels.append("exact_input_identity")
        statuses[:] = 1
        first[:] = np.nan
    else:
        if call_table is None or call_table["model"] != model or call_table["parameters"] != p:
            raise ValueError("oracle requires the bound actual independent call table")
        if call_table.get("surface_signature") != _field_binding(surface)[1]:
            raise ValueError("oracle field differs from bound independent call table")
        dates, spots = np.asarray(call_table["dates"]), np.asarray(call_table["query_spots"])
        at_date = np.flatnonzero(np.isclose(dates, date, atol=1e-12, rtol=0))
        if len(at_date) != 1:
            raise ValueError("call table must include exactly this calendar date")
        for query_id, (s, q) in zip(query_ids, queries, strict=True):
            at_spot = np.flatnonzero(np.isclose(spots, s, atol=1e-12, rtol=0))
            if len(at_spot) != 1:
                raise ValueError("call table must include exact baseline and all S bumps")
            curves = np.asarray(call_table["prices"])[:, at_date[0], at_spot[0], :]
            fit = fit_independent_quote(
                call_table["state_nodes"], curves[-1], q, model=model, spot=s, query_id=query_id
            )
            fit["refinement_fits"] = [
                fit_independent_quote(
                    call_table["state_nodes"], curve, q, model=model, spot=s, query_id=query_id
                )
                for curve in curves
            ]
            fit["residual_scope"] = "independent_full_domain_physical_state_cubic_interpolant"
            fits.append(fit)
        base = fits[0]
        hv = 0.0001 if model == "heston" else 0.001
        if base["solver_status"] == "unique_root" and base["state"] <= 2 * hv:
            refinement_status = {
                "status": "unavailable_derivative_boundary",
                "reason": "fixed symmetric state bumps leave positive state space",
                "state": base["state"],
                "fixed_state_bump": hv,
                "width_multipliers": [1.0, 0.5, 2.0],
                "full_domain_bounds": base["full_domain_bounds"],
            }
        elif base["solver_status"] == "unique_root" and not _expired(deadline):
            controls = call_table["controls"]
            permitted = {"space_nodes", "time_steps", "log_half_width", "upper", "quadrature_limit"}
            wall, cpu = time.perf_counter(), time.process_time()
            refinement = selected_call_refinement(
                p,
                surface,
                model=model,
                date=date,
                spot=spot,
                state=base["state"],
                spot_bump=spot_bump,
                wall_cap_seconds=None
                if deadline is None
                else max(0.0, deadline - time.perf_counter()),
                deadline_wall=deadline,
                **{k: v for k, v in controls.items() if k in permitted},
            )
            refinement_status = {
                "status": refinement["status"],
                "reason": "direct independent refinement retained",
            }
            cv = float(refinement["state_derivative"])
            scale = 0.04 if model == "heston" else 1.0
            curve_diagnostics = {
                "scope": "baseline independent finite call curve versus direct CF/PDE",
                "price_residual": float(refinement["price"] - quote),
                "state_derivative_difference": float(base["Ctheta"] - cv),
                "scaled_state_derivative_difference": float(scale * abs(base["Ctheta"] - cv)),
                "curve_condition_number": float(base["condition_number"]),
                "direct_condition_number": 0.01 / (scale * abs(cv)) if cv else np.inf,
                "reference_kind": "empirical_numerical_not_exact_truth",
            }
            expenses.append(
                {
                    "job_id": "independent-selected-call",
                    "scope": "independent_call_refinement",
                    **_timing(wall, cpu, deadline),
                    "path_steps": 0,
                    "original_path_count": 0,
                }
            )
        calendars = [_calendar(date, memory_count, level) for level in levels]
        fine_steps = len(calendars[1][0]) - 1
        for start, stop, paired, driver in _driver_chunks(
            n_paths, fine_steps, seed, chunk_paths, normals, deadline
        ):
            drivers.append(driver)
            expenses.append(
                {
                    "job_id": f"oracle-driver-{start}",
                    "scope": "independent_oracle_driver",
                    **driver,
                    "path_steps": (stop - start) * fine_steps,
                }
            )
            for k, (times, indices) in enumerate(calendars):
                for j, fit in enumerate(fits):
                    if _expired(deadline):
                        break
                    wall, cpu = time.perf_counter(), time.process_time()
                    ran = fit["solver_status"] == "unique_root"
                    if ran:
                        raw = direct_asian_price(
                            p,
                            surface,
                            model=model,
                            calendar_times=times,
                            fixing_indices=indices,
                            spot=fit["spot"],
                            state=fit["state"],
                            memory_sum=memory_sum,
                            memory_count=memory_count,
                            seed=seed,
                            n_paths=stop - start,
                            normals=paired[k],
                        )
                        payoff[k, j, start:stop] = raw["samples"]
                        statuses[k, j, start:stop] = _status_codes(
                            raw["path_status"], status_labels
                        )
                        first[k, j, start:stop] = raw["first_failure_date"]
                    if not ran:
                        statuses[k, j, start:stop] = _status_codes(
                            np.full(stop - start, "unknown_quote_fit"), status_labels
                        )
                    expenses.append(
                        {
                            "job_id": f"oracle-{start}-{levels[k]}-{query_ids[j]}",
                            "scope": "independent_asian_quote_oracle",
                            "query_id": query_ids[j],
                            "level": levels[k],
                            "path_range": [start, stop],
                            "original_path_count": n_paths,
                            "processed_path_count": stop - start,
                            "path_steps": (stop - start) * (len(times) - 1) if ran else 0,
                            "attempt_status": "measured" if ran else "rejected_quote_fit",
                            "reason": fit["reason"],
                            **_timing(wall, cpu, deadline),
                        }
                    )
    sample_levels, width_levels = zip(
        *[_oracle_arrays(v, spot_bump, quote_bump) for v in payoff], strict=True
    )
    sample_levels, width_levels = np.asarray(sample_levels), np.asarray(width_levels)
    fine = sample_levels[1]
    summary = _sample_summary(fine, exact=exact)
    within = exact or all(v["operational_status"] == "within_envelope" for v in fits)
    return {
        **summary,
        "schema": "rb-f04-independent-quote-oracle-v1",
        "model": model,
        "seed": int(seed),
        "N": n_paths,
        "original_path_count": n_paths,
        "path_indices": np.arange(n_paths),
        "input_state": {
            "date": date,
            "spot": spot,
            "quote": quote,
            "memory_sum": memory_sum,
            "memory_count": memory_count,
        },
        "query_ids": query_ids,
        "query_fits": fits,
        "width_multipliers": np.array([1.0, 0.5, 2.0]),
        "spot_bump": spot_bump,
        "quote_bump": quote_bump,
        "selected_width_index": 1,
        "payoff_samples": payoff[1],
        "samples": fine,
        "width_position_samples": width_levels[1],
        "block_means": _blocks(fine),
        "block_payoff_means": _blocks(payoff[1].T).T,
        "three_width_greek_means": width_levels[1].mean(axis=1),
        "width_covariance": np.cov(
            width_levels[1].transpose(1, 0, 2).reshape(n_paths, 6), rowvar=False
        )
        / n_paths,
        "path_status": statuses[1],
        "path_status_labels": np.asarray(status_labels),
        "path_status_encoding": "uint16_dictionary",
        "first_failure_date": first[1],
        "driver_map": drivers,
        "cap_evidence": _cap_receipt(
            wall_cap_seconds, started, statuses, status_labels, deadline_wall=deadline
        ),
        "call_table": call_table,
        "call_refinements": refinement,
        "call_refinement_status": refinement_status,
        "independent_curve_diagnostics": curve_diagnostics,
        "expenses": expenses,
        "scheme_refinement": {
            "levels": levels,
            "samples": sample_levels,
            "payoff_samples": payoff,
            "paired_difference_samples": sample_levels[1] - sample_levels[0],
            "path_status": statuses,
            "path_status_labels": np.asarray(status_labels),
            "path_status_encoding": "uint16_dictionary",
            "first_failure_date": first,
            "block_difference_means": _blocks(sample_levels[1] - sample_levels[0]),
        },
        "operational_status": "within_envelope" if within else "unknown",
        "financial_qualification": "unknown",
        "qualification_reason": "raw independent measurements require saved financial checks"
        if within
        else "original query fit or conditioning is unsupported",
        "exact_branch": "settled" if memory_count == 12 else "linear" if exact else None,
    }


def premium_reference(
    parameters,
    *,
    seed,
    n_paths=65536,
    steps_per_year=1536,
    chunk_paths=4096,
    wall_cap_seconds=None,
    deadline_wall=None,
):
    """Execute the exact reserved independent Heston PRICE-only premium pilot.

    Original 65536 IID paths, 1536 fine steps and reserved premium seed are
    mandatory. Coarse 768 uses aggregated fine increments. This function does
    not fabricate a small-N premium or grant precision qualification. Toy
    numerical tests use direct_asian_price instead.
    """
    import time

    started = time.perf_counter()
    deadline = _deadline(wall_cap_seconds, started, deadline_wall=deadline_wall)
    reserved = int(np.random.SeedSequence([2026100904, 8, 0]).generate_state(1)[0])
    if n_paths != 65536 or steps_per_year != 1536 or int(seed) != reserved:
        raise ValueError("premium requires original N=65536, grid=1536 and reserved seed")
    p = _parameters(parameters)
    expected = dict(
        spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7
    )
    if chunk_paths < 16 or chunk_paths % 16:
        raise ValueError("premium chunks must preserve 16 original IID blocks")
    if p != expected:
        raise ValueError("premium requires the original synthetic Heston parameters")
    samples = np.full((2, n_paths), np.nan)
    status_labels = ["unmeasured"]
    statuses = np.zeros((2, n_paths), dtype=np.uint16)
    first = np.full((2, n_paths), np.nan)
    expenses, drivers = [], []
    calendars = [_calendar(0.0, 0, level) for level in [768, 1536]]
    for start, stop, paired, driver in _driver_chunks(
        n_paths, 1536, seed, chunk_paths, deadline=deadline
    ):
        drivers.append(driver)
        expenses.append(
            {
                "job_id": f"premium-driver-{start}",
                "scope": "independent_premium_driver",
                **driver,
                "path_steps": (stop - start) * 1536,
            }
        )
        for k, (times, indices) in enumerate(calendars):
            if _expired(deadline):
                break
            wall, cpu = time.perf_counter(), time.process_time()
            raw = direct_asian_price(
                p,
                None,
                model="heston",
                calendar_times=times,
                fixing_indices=indices,
                spot=100.0,
                state=0.04,
                memory_sum=0.0,
                memory_count=0,
                seed=seed,
                n_paths=stop - start,
                normals=paired[k],
            )
            samples[k, start:stop] = raw["samples"]
            statuses[k, start:stop] = _status_codes(raw["path_status"], status_labels)
            first[k, start:stop] = raw["first_failure_date"]
            expenses.append(
                {
                    "job_id": f"premium-{start}-{[768, 1536][k]}",
                    "scope": "independent_premium_price_only",
                    "level": [768, 1536][k],
                    "path_range": [start, stop],
                    "original_path_count": n_paths,
                    "processed_path_count": stop - start,
                    "path_steps": (stop - start) * (len(times) - 1),
                    **_timing(wall, cpu, deadline),
                }
            )
    summary = _sample_summary(samples[1])
    difference = samples[1] - samples[0]
    paired_summary = _sample_summary(difference)
    return {
        **summary,
        "schema": "rb-f04-independent-premium-v1",
        "model": "heston",
        "parameters": p,
        "seed": int(seed),
        "N": n_paths,
        "original_path_count": n_paths,
        "steps_per_year": 1536,
        "levels": [768, 1536],
        "path_indices": np.arange(n_paths),
        "samples": samples,
        "price_only": True,
        "value": float(summary["mean"]),
        "standard_error": float(summary["standard_errors"]),
        "paired_difference_samples": difference,
        "paired_difference_mean": float(paired_summary["mean"]),
        "paired_difference_standard_error": float(paired_summary["standard_errors"]),
        "scheme_error": abs(float(paired_summary["mean"])),
        "path_status": statuses,
        "path_status_labels": np.asarray(status_labels),
        "path_status_encoding": "uint16_dictionary",
        "first_failure_date": first,
        "block_means": _blocks(samples.T).T,
        "driver_map": drivers,
        "cap_evidence": _cap_receipt(
            wall_cap_seconds, started, statuses, status_labels, deadline_wall=deadline
        ),
        "expenses": expenses,
        "financial_qualification": "unknown",
        "qualification_reason": "MC and scheme evidence require saved financial checks",
    }
