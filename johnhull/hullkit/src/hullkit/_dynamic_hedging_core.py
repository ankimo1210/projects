"""Private calendar simulation and self-financing accounting for RB-F04.

All shocks are caller supplied. Failures retain the original path denominator;
no variance/price clipping or replacement holdings repair invalid paths.
"""

from __future__ import annotations

import math

import numpy as np

from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid


def cir_implicit_step(
    v: np.ndarray, z_v: np.ndarray, dt: float, parameters: HestonParameters
) -> np.ndarray:
    """Positive Lamperti drift-implicit CIR step, exact deterministic xi=0 branch."""
    v, z_v = np.broadcast_arrays(np.asarray(v, dtype=float), np.asarray(z_v, dtype=float))
    if not math.isfinite(dt) or dt <= 0 or np.any(~np.isfinite(v)) or np.any(v < 0):
        raise ValueError("require finite dt>0 and finite v>=0")
    if parameters.xi == 0:
        return parameters.theta + (v - parameters.theta) * math.exp(-parameters.kappa * dt)
    if np.any(~np.isfinite(z_v)):
        raise ValueError("variance shocks must be finite")
    a = (4 * parameters.kappa * parameters.theta - parameters.xi**2) / 8
    if a <= 0:
        raise ValueError("positive CIR scheme requires 4*kappa*theta > xi**2")
    d = 1 + parameters.kappa * dt / 2
    u = np.sqrt(v) + parameters.xi / 2 * math.sqrt(dt) * z_v
    # hypot avoids squaring very large u; negative root is rationalized.
    root = np.hypot(u, math.sqrt(4 * d * a * dt))
    y = np.empty(u.shape)
    positive = u >= 0
    y[positive] = (u[positive] + root[positive]) / (2 * d)
    y[~positive] = 2 * a * dt / (root[~positive] - u[~positive])
    return y**2


def moment_certificate(
    parameters: HestonParameters, horizon: float, p: int = 4, epsilon: float = 0.01
) -> dict:
    """Sufficient finite-grid stock moment bound, without a convergence assertion.

    Gaussian coefficient bounds the strict-lower-triangle Frobenius bound for
    every uniform finite grid. Backward MGF evidence is provided independently
    for the four protocol step levels, using lambda=2*p**2-p.
    """
    if not math.isfinite(horizon) or horizon <= 0 or p < 1 or int(p) != p:
        raise ValueError("require horizon>0 and positive integer moment p")
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    a = (4 * parameters.kappa * parameters.theta - parameters.xi**2) / 8
    c = parameters.xi / 2
    lam = 2 * p**2 - p
    coefficient = lam * (1 + epsilon) * c**2 * horizon**2
    rows = []
    for level in (192, 384, 768, 1536):
        steps = math.ceil(level * horizon)
        dt = horizon / steps
        d = 1 + parameters.kappa * dt / 2
        eta = 0.0
        denominators = []
        constant = 0.0
        for _ in range(steps):
            denominator = d**2 - 2 * c**2 * dt * eta
            denominators.append(denominator)
            if denominator <= 0 or not math.isfinite(denominator):
                eta = math.nan
                constant = math.nan
                break
            constant += 2 * a * dt * eta / d - 0.5 * math.log(denominator / d**2)
            eta = lam * dt + eta / denominator
        rows.append(
            {
                "steps_per_year": level,
                "steps": steps,
                "dt": dt,
                "denominators": np.asarray(denominators),
                "min_denominator": min(denominators),
                "eta": eta,
                "log_bound_at_v0": constant + eta * parameters.v0,
                "qualified": bool(math.isfinite(eta) and min(denominators) > 0),
            }
        )
    scheme_valid = parameters.xi == 0 or a > 0
    return {
        "qualified": bool(
            scheme_valid and coefficient < 1 and all(row["qualified"] for row in rows)
        ),
        "scope": "fixed_finite_grid_sufficient_bound",
        "p": p,
        "epsilon": epsilon,
        "horizon": horizon,
        "lambda": lam,
        "gaussian_quadratic_coefficient": coefficient,
        "backward_mgf": rows,
        "positive_scheme_admissible": scheme_valid,
        "continuous_model_or_uniform_convergence_certified": False,
        "excluded_cm2_lognormal": "positive exponential moments of nondegenerate lognormal variance diverge",
    }


def _times_axis(times, minimum=2):
    times = np.asarray(times, dtype=float)
    if (
        times.ndim != 1
        or times.size < minimum
        or np.any(~np.isfinite(times))
        or times[0] < 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError(
            "times must be finite nonnegative strictly increasing dates, length too short"
        )
    return times


def _recorder_inputs(normals, times, record_indices):
    times = _times_axis(times)
    normals = np.asarray(normals, dtype=float)
    indices = np.asarray(record_indices)
    if normals.ndim != 3 or normals.shape[1:] != (times.size - 1, 2) or normals.shape[0] == 0:
        raise ValueError("normals must have shape (N,steps,2), N>0")
    if (
        indices.ndim != 1
        or indices.size == 0
        or indices.dtype.kind not in "iu"
        or np.any(indices < 0)
        or np.any(indices >= times.size)
        or np.any(np.diff(indices) <= 0)
    ):
        raise ValueError("record_indices must be strictly increasing indices inside times")
    return normals, times, indices


def _initial_vector(value, default, n):
    return np.array(
        np.broadcast_to(np.asarray(default if value is None else value, dtype=float), (n,)),
        copy=True,
    )


def _failure(mask, reasons, failed, reason):
    fresh = mask & failed
    reasons[fresh] = reason if isinstance(reason, str) else reason[fresh]
    mask[fresh] = False


def _records_result(spots, variances, indices, mask, reasons, diagnostics):
    diagnostics.update(original_path_count=len(mask), failed_path_count=int(np.sum(~mask)))
    return {
        "spot": spots[:, indices],
        "variance": variances[:, indices],
        "path_mask": mask,
        "reasons": reasons,
        "diagnostics": diagnostics,
    }


def heston_records(
    parameters: HestonParameters,
    normals: np.ndarray,
    times: np.ndarray,
    record_indices: np.ndarray,
    *,
    spot=None,
    variance=None,
) -> dict:
    """Record adapted old-v stock and positive CIR on absolute calendar dates."""
    normals, times, indices = _recorder_inputs(normals, times, record_indices)
    if parameters.xi > 0 and 4 * parameters.kappa * parameters.theta <= parameters.xi**2:
        raise ValueError("positive CIR scheme requires 4*kappa*theta > xi**2")
    n = len(normals)
    spots = np.full((n, len(indices)), np.nan)
    variances = np.full_like(spots, np.nan)
    current_s = _initial_vector(spot, parameters.spot, n)
    current_v = _initial_vector(variance, parameters.v0, n)
    mask = np.ones(n, dtype=bool)
    reasons = np.full(n, "ok", dtype="<U64")
    _failure(
        mask,
        reasons,
        ~np.isfinite(current_s) | (current_s <= 0) | ~np.isfinite(current_v) | (current_v < 0),
        "invalid_initial_state",
    )
    current_s[~mask] = current_v[~mask] = np.nan
    record_map = {int(date): j for j, date in enumerate(indices)}
    if 0 in record_map:
        spots[:, record_map[0]] = current_s
        variances[:, record_map[0]] = current_v
    for i, dt in enumerate(np.diff(times)):
        _failure(mask, reasons, ~np.isfinite(normals[:, i]).all(axis=1), "nonfinite_normal")
        active = np.flatnonzero(mask)
        zs = normals[active, i, 0]
        zv = parameters.rho * zs + math.sqrt(1 - parameters.rho**2) * normals[active, i, 1]
        old_v = current_v[active]
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            current_s[active] *= np.exp(
                (parameters.rate - parameters.dividend_yield - old_v / 2) * dt
                + np.sqrt(old_v * dt) * zs
            )
            current_v[active] = cir_implicit_step(old_v, zv, float(dt), parameters)
        _failure(
            mask,
            reasons,
            ~np.isfinite(current_s)
            | (current_s <= 0)
            | ~np.isfinite(current_v)
            | ((current_v <= 0) if parameters.xi else (current_v < 0)),
            "nonfinite_transition",
        )
        current_s[~mask] = current_v[~mask] = np.nan
        if i + 1 in record_map:
            spots[:, record_map[i + 1]] = current_s
            variances[:, record_map[i + 1]] = current_v
    return _records_result(
        spots,
        variances,
        np.arange(len(indices)),
        mask,
        reasons,
        {"unsupported_count": 0, "wing_count": 0, "early_proxy_count": 0},
    )


def local_records(
    parameters: HestonParameters,
    surface: LocalVarianceGrid,
    normals: np.ndarray,
    times: np.ndarray,
    record_indices: np.ndarray,
    *,
    spot=None,
    multiplier=1.0,
) -> dict:
    """Calendar midpoint/left-spot simulation with labelled local field support.

    Recorded variance at a left date is the effective outgoing interval
    variance; the terminal date carries the last interval's effective variance.
    Counts cover all original path/step evaluations; local_status covers the
    recorded dates only. Internal states are not retained.
    """
    normals, times, indices = _recorder_inputs(normals, times, record_indices)
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("multiplier must be finite and positive")
    n = len(normals)
    spots = np.full((n, len(indices)), np.nan)
    variances = np.full_like(spots, np.nan)
    statuses = np.full((n, len(indices)), "not_evaluated", dtype="<U32")
    current_s = _initial_vector(spot, parameters.spot, n)
    mask = np.ones(n, dtype=bool)
    reasons = np.full(n, "ok", dtype="<U64")
    _failure(mask, reasons, ~np.isfinite(current_s) | (current_s <= 0), "invalid_initial_state")
    current_s[~mask] = np.nan
    record_map = {int(date): j for j, date in enumerate(indices)}
    diagnostics = {"unsupported_count": 0, "wing_count": 0, "early_proxy_count": 0}
    for i, dt in enumerate(np.diff(times)):
        if i in record_map:
            spots[:, record_map[i]] = current_s
        _failure(mask, reasons, ~np.isfinite(normals[:, i, 0]), "nonfinite_normal")
        active = np.flatnonzero(mask)
        evaluated = surface.evaluate(float((times[i] + times[i + 1]) / 2), current_s[active])
        status = np.full(n, "not_evaluated", dtype="<U32")
        effective = np.full(n, np.nan)
        status[active] = evaluated["status"]
        effective[active] = multiplier * evaluated["variance"]
        unsupported = np.char.startswith(status, "unsupported")
        diagnostics["unsupported_count"] += int(np.sum(unsupported))
        diagnostics["wing_count"] += int(np.sum(np.char.find(status, "wing") >= 0))
        diagnostics["early_proxy_count"] += int(np.sum(np.char.startswith(status, "early_time")))
        _failure(mask, reasons, unsupported, status)
        _failure(
            mask, reasons, ~np.isfinite(effective) | (effective <= 0), "invalid_local_variance"
        )
        effective[~mask] = np.nan
        if i in record_map:
            variances[:, record_map[i]] = effective
            statuses[:, record_map[i]] = status
        active = np.flatnonzero(mask)
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            current_s[active] *= np.exp(
                (parameters.rate - parameters.dividend_yield - effective[active] / 2) * dt
                + np.sqrt(effective[active] * dt) * normals[active, i, 0]
            )
        _failure(mask, reasons, ~np.isfinite(current_s) | (current_s <= 0), "nonfinite_transition")
        current_s[~mask] = np.nan
    if len(times) - 1 in record_map:
        j = record_map[len(times) - 1]
        spots[:, j] = current_s
        effective[~mask] = np.nan
        variances[:, j] = effective
        statuses[:, j] = status
    diagnostics["local_status"] = statuses
    return _records_result(spots, variances, np.arange(len(indices)), mask, reasons, diagnostics)


def asian_memory(
    record_spots: np.ndarray, record_times: np.ndarray, fixing_times: np.ndarray
) -> dict:
    """Observed sum A and scheduled counts n,m, adding fixing before rebalance.

    Initial spot is excluded unless explicitly listed as a fixing. Every past
    fixing must be represented by a recorded date; future fixing dates remain
    pending. A missing observation is never interpolated.
    """
    times = _times_axis(record_times, minimum=1)
    spots = np.asarray(record_spots, dtype=float)
    fixings = np.asarray(fixing_times, dtype=float)
    if spots.ndim != 2 or spots.shape[1] != times.size:
        raise ValueError("record_spots must have shape (N,record dates)")
    if (
        fixings.ndim != 1
        or fixings.size == 0
        or np.any(~np.isfinite(fixings))
        or np.any(fixings <= 0)
        or np.any(np.diff(fixings) <= 0)
    ):
        raise ValueError("fixing_times must be finite positive increasing dates")
    increments = np.zeros_like(spots)
    counts = np.zeros(len(times), dtype=int)
    for fixing in fixings[fixings <= times[-1] + 1e-12]:
        matches = np.flatnonzero(np.isclose(times, fixing, rtol=0.0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError("every past fixing requires one recorded observation")
        i = matches[0]
        increments[:, i] = np.where(
            np.isfinite(spots[:, i]) & (spots[:, i] > 0), spots[:, i], np.nan
        )
        counts[i] += 1
    n = np.cumsum(counts)
    A = np.cumsum(increments, axis=1)
    return {"A": A, "n": n, "m": len(fixings) - n}


def cash_account(
    times: np.ndarray,
    prices: np.ndarray,
    holdings: np.ndarray,
    payoff: np.ndarray,
    *,
    premium: float,
    rate: float,
    cashflows=None,
    cost_rates=None,
) -> dict:
    """Cash recursion plus independent discounted gains, including one liquidation.

    Holdings apply on each following interval. At event i>0 the previous
    holding receives cashflows[:,i] before trading. Cashflows at the initial
    date have zero entitled holding. Prices are ex-dividend, and terminal
    traded-call mid recovery is not a traded-call payoff. Claim is paid once.
    Discounting is relative to times[0]; units are the reporting currency.
    """
    times = _times_axis(times)
    prices, holdings, payoff = (np.asarray(x, dtype=float) for x in (prices, holdings, payoff))
    if (
        prices.ndim != 3
        or prices.shape[0] == 0
        or prices.shape[1] != len(times)
        or prices.shape[2] == 0
    ):
        raise ValueError("prices must have shape (N,m+1,d)")
    n, dates, d = prices.shape
    if holdings.shape != (n, dates - 1, d) or payoff.shape != (n,):
        raise ValueError("holdings/payoff shapes must be (N,m,d)/(N,)")
    if not math.isfinite(premium) or not math.isfinite(rate):
        raise ValueError("premium and rate must be finite")
    cf = np.zeros_like(prices) if cashflows is None else np.asarray(cashflows, dtype=float)
    fees = np.zeros(d) if cost_rates is None else np.asarray(cost_rates, dtype=float)
    if (
        cf.shape != prices.shape
        or fees.shape != (d,)
        or np.any(~np.isfinite(fees))
        or np.any(fees < 0)
    ):
        raise ValueError(
            "cashflows must match prices and cost_rates must be finite nonnegative (d,)"
        )
    cash = np.full((n, dates), np.nan)
    costs = np.full_like(cash, np.nan)
    mask = np.ones(n, dtype=bool)
    reasons = np.full(n, "ok", dtype="<U64")
    previous = np.zeros((n, d))
    balance = np.full(n, premium)
    for i in range(dates):
        current = holdings[:, i] if i < dates - 1 else np.zeros((n, d))
        invalid = (~np.isfinite(prices[:, i]) | (prices[:, i] < 0)).any(axis=1) | ~np.isfinite(
            current
        ).all(axis=1)
        if i:
            invalid |= ~np.isfinite(cf[:, i]).all(axis=1)
        if i == dates - 1:
            invalid |= ~np.isfinite(payoff)
        _failure(mask, reasons, invalid, "invalid_cash_event")
        with np.errstate(over="ignore", invalid="ignore"):
            if i:
                balance = balance * np.exp(rate * (times[i] - times[i - 1])) + np.sum(
                    previous * cf[:, i], axis=1
                )
            change = current - previous
            costs[:, i] = np.sum(fees * prices[:, i] * np.abs(change), axis=1)
            balance = balance - np.sum(change * prices[:, i], axis=1) - costs[:, i]
            if i == dates - 1:
                balance = balance - payoff
        _failure(mask, reasons, ~np.isfinite(balance), "nonfinite_cash_balance")
        balance[~mask] = np.nan
        cash[:, i] = balance
        costs[~mask, i] = np.nan
        previous = current
    with np.errstate(over="ignore", invalid="ignore"):
        discount = np.exp(-rate * (times - times[0]))
    # Recompute from discounted ex-dividend increments rather than cash recursion.
    with np.errstate(over="ignore", invalid="ignore"):
        increments = (
            discount[None, 1:, None] * (prices[:, 1:] + cf[:, 1:])
            - discount[None, :-1, None] * prices[:, :-1]
        )
        extended = np.concatenate([np.zeros((n, 1, d)), holdings, np.zeros((n, 1, d))], axis=1)
        gain_costs = np.sum(fees * prices * np.abs(np.diff(extended, axis=1)), axis=2)
        gain_pnl = (
            premium
            + np.sum(holdings * increments, axis=(1, 2))
            - np.sum(discount * gain_costs, axis=1)
            - discount[-1] * payoff
        )
        discounted_pnl = discount[-1] * cash[:, -1]
    _failure(
        mask,
        reasons,
        ~np.isfinite(gain_pnl) | ~np.isfinite(discounted_pnl),
        "nonfinite_discounted_account",
    )
    gain_pnl[~mask] = discounted_pnl[~mask] = cash[~mask, -1] = np.nan
    return {
        "cash": cash,
        "costs": costs,
        "pnl": cash[:, -1],
        "discounted_pnl": discounted_pnl,
        "discounted_gain_pnl": gain_pnl,
        "path_mask": mask,
        "reasons": reasons,
        "diagnostics": {"original_path_count": n, "failed_path_count": int(np.sum(~mask))},
    }
