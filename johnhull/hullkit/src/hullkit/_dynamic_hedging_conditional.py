"""Saved, normalized Asian primitives with a same-driver auxiliary GBM control.

Calendar times are absolute years; fixing delays are years from the restart.
``f`` is the undiscounted expectation of ``(sum(S_fix / spot) - x)+``.
The caller supplies IID stock/independent variance normals; no RNG is used.
Geometric auxiliary prices are known for a separate constant-volatility GBM,
not for the Heston or local model. All paths remain in the denominator.
"""

from __future__ import annotations

import hashlib

import numpy as np
from scipy.special import log_ndtr, ndtr

from ._dynamic_hedging_core import cir_implicit_step
from ._heston_local_surface import HestonParameters


def conditional_tail(b, c, mu, sigma, x) -> dict:
    """Integrate ``(b + c exp(mu + sigma Z) - x)+`` and its x derivative.

    Inputs broadcast. Nonnegative ``c`` and ``sigma`` are required. At a
    deterministic atom the value exists, but the ordinary x derivative is
    unknown; it is returned as NaN with ``unknown_atom`` status. ``f_xx``
    is the ordinary density away from this atom, not a Dirac mass.
    """
    b, c, mu, sigma, x = np.broadcast_arrays(
        *[np.asarray(v, dtype=float) for v in (b, c, mu, sigma, x)]
    )
    shape = b.shape
    f = np.full(shape, np.nan)
    fx = np.full(shape, np.nan)
    fxx = np.full(shape, np.nan)
    status = np.full(shape, "invalid", dtype="<U40")
    valid = (
        np.isfinite(b)
        & np.isfinite(c)
        & np.isfinite(mu)
        & np.isfinite(sigma)
        & np.isfinite(x)
        & (c >= 0)
        & (sigma >= 0)
    )
    stochastic = valid & (sigma > 0) & (c > 0)
    k = x - b
    linear = stochastic & (k <= 0)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        expected = c * np.exp(mu + sigma**2 / 2)
        f[linear] = expected[linear] - k[linear]
    fx[linear] = -1
    fxx[linear] = 0
    status[linear] = "linear"
    positive = stochastic & (k > 0)
    d2 = (np.log(c[positive]) + mu[positive] - np.log(k[positive])) / sigma[positive]
    d1 = d2 + sigma[positive]
    # Log subtraction retains small positive tails without clipping a price.
    log_first = np.log(c[positive]) + mu[positive] + sigma[positive] ** 2 / 2 + log_ndtr(d1)
    log_second = np.log(k[positive]) + log_ndtr(d2)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        f[positive] = np.exp(log_first) * -np.expm1(log_second - log_first)
        fxx[positive] = np.exp(-(d2**2) / 2) / (np.sqrt(2 * np.pi) * k[positive] * sigma[positive])
    fx[positive] = -ndtr(d2)
    status[positive] = "ready"
    deterministic = valid & ~stochastic
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        terminal = b + c * np.exp(mu)
    f[deterministic] = np.maximum(terminal[deterministic] - x[deterministic], 0)
    fx[deterministic] = -(terminal[deterministic] > x[deterministic]).astype(float)
    fxx[deterministic] = 0
    status[deterministic] = "deterministic"
    atom = deterministic & (terminal == x)
    fx[atom] = np.nan
    fxx[atom] = np.nan
    status[atom] = "unknown_atom"
    nonfinite = valid & (~np.isfinite(f) | (~atom & ~np.isfinite(fx)))
    status[nonfinite] = "invalid"
    return {"f": f, "f_x": fx, "f_xx": fxx, "status": status}


def _delays(delays, expiry_delay):
    delays = np.asarray(delays, dtype=float)
    if (
        delays.ndim != 1
        or not np.isfinite(delays).all()
        or np.any(delays <= 0)
        or np.any(np.diff(delays) <= 0)
        or not np.isfinite(expiry_delay)
        or expiry_delay < 0
        or np.any(delays > expiry_delay)
    ):
        raise ValueError("fixing delays must be positive, increasing and within expiry")
    return delays


def _geometric_law(variance, delays, drift):
    if not delays.size:
        return 0.0, 0.0
    mean_log_ratio = (drift - variance / 2) * np.mean(delays)
    log_variance = variance * np.minimum.outer(delays, delays).mean()
    return mean_log_ratio, np.sqrt(log_variance)


def auxiliary_geometric_mean(
    spot: float,
    variance: float,
    fixing_delays: np.ndarray,
    expiry_delay: float,
    *,
    rate: float,
    dividend_yield: float,
    memory_sum: float,
    strike: float,
    total_fixings: int = 12,
) -> float:
    """Discounted currency price of ``m/N (G - (N K-A)/m)+`` under GBM.

    ``G`` uses only the remaining actual fixing times, and the payout is at
    ``expiry_delay``. Past arithmetic memory ``A`` is in currency. With no
    remaining fixings this is the discounted settled arithmetic payoff.
    """
    delays = _delays(fixing_delays, expiry_delay)
    if (
        not np.isfinite([spot, variance, rate, dividend_yield, memory_sum, strike]).all()
        or spot <= 0
        or variance < 0
        or total_fixings < 1
        or int(total_fixings) != total_fixings
        or delays.size > total_fixings
    ):
        raise ValueError("finite values, spot>0, variance>=0 and positive fixing count required")
    discount = np.exp(-rate * expiry_delay)
    if not delays.size:
        return float(discount * max(memory_sum / total_fixings - strike, 0))
    mu, sigma = _geometric_law(variance, delays, rate - dividend_yield)
    value = conditional_tail(0, delays.size * spot, mu, sigma, total_fixings * strike - memory_sum)
    return float(discount * value["f"] / total_fixings)


def _local_variance(surface, time, stock):
    evaluated = surface.evaluate(float(time), stock)
    variance = np.asarray(evaluated["variance"], dtype=float)
    status = np.asarray(evaluated["status"], dtype=str)
    if variance.shape != stock.shape or status.shape != stock.shape:
        raise ValueError("local surface variance/status must preserve spot shape")
    supported = ~np.char.startswith(status, "unsupported")
    valid = supported & np.isfinite(variance) & (variance >= 0)
    return variance, status, valid


def teacher_primitives(
    model: str,
    parameters: HestonParameters,
    normals: np.ndarray,
    *,
    calendar_times: np.ndarray,
    fixing_indices: np.ndarray,
    spot: float,
    state: float,
    memory_count: int,
    surface=None,
    compact_status: bool = False,
) -> dict:
    """Simulate to the last fixing and retain its conditional/GBM primitives.

    ``normals`` is ``(original paths, calendar intervals, 2)``. Factor zero
    drives stock and the auxiliary; factor one is the independent variance
    driver before rho correlation. Fixing indices address ``calendar_times``
    and exclude the restart spot. Heston state is variance, local state is a
    fixed forecast multiplier. Local coefficients use absolute midpoints.
    ``aux_logG_prefix`` is a normalized log geometric mean excluding the
    last stock normal, which enters through ``aux_last_loading``.
    With compact_status=True all path/step statuses use lossless uint8 codes
    and local_step_status_labels; the legacy Unicode default is unchanged.
    """
    normals = np.asarray(normals, dtype=float)
    times = np.asarray(calendar_times, dtype=float)
    fixing_input = np.asarray(fixing_indices)
    if (
        model not in ("heston", "local")
        or normals.ndim != 3
        or normals.shape[2] != 2
        or normals.shape[0] < 1
        or times.ndim != 1
        or times.size != normals.shape[1] + 1
        or not np.isfinite(times).all()
        or times[0] < 0
        or np.any(np.diff(times) <= 0)
        or fixing_input.ndim != 1
        or not np.isfinite(fixing_input).all()
        or np.any(fixing_input != fixing_input.astype(int))
        or not np.isfinite([spot, state]).all()
        or spot <= 0
        or state < 0
        or not isinstance(memory_count, (int, np.integer))
        or not 0 <= memory_count <= 12
    ):
        raise ValueError("invalid model, calendar, drivers, state or memory count")
    fixings = fixing_input.astype(int)
    if (
        np.any(fixings <= 0)
        or np.any(fixings >= times.size)
        or np.any(np.diff(fixings) <= 0)
        or fixings.size + memory_count > 12
        or (model == "local" and (surface is None or state <= 0))
    ):
        raise ValueError(
            "fixings must be increasing future calendar indices; local requires a field"
        )
    paths = normals.shape[0]
    delays = times[fixings] - times[0]
    expiry_delay = float(times[-1] - times[0])
    drift = parameters.rate - parameters.dividend_yield
    b = np.zeros(paths)
    stock = np.full(paths, spot, dtype=float)
    variance = np.full(paths, state, dtype=float)
    aux_log_stock = np.zeros(paths)
    aux_log_sum = np.zeros(paths)
    path_mask = np.ones(paths, dtype=bool)
    reasons = np.full(paths, "", dtype="<U128")
    status_shape = (paths, int(fixings[-1]) if fixings.size else 0)
    step_status = (
        np.zeros(status_shape, dtype=np.uint8)
        if compact_status
        else np.full(status_shape, "", dtype="<U64")
    )
    status_labels = [""]
    status_codes = {"": 0}

    def record_status(rows, step, values):
        if not compact_status:
            step_status[rows, step] = values
            return
        values = np.broadcast_to(np.asarray(values, dtype=str), (len(rows),))
        for label in np.unique(values):
            text = str(label)
            if text not in status_codes:
                if len(status_labels) >= 256:
                    raise ValueError("compact step status supports at most 256 categories")
                status_codes[text] = len(status_labels)
                status_labels.append(text)
            step_status[rows[values == label], step] = status_codes[text]

    control_status = "not_required_settled"
    aux_first_midpoint = np.nan
    control_variance = 0.0
    if fixings.size:
        if model == "heston":
            tau = expiry_delay
            control_variance = parameters.theta + (state - parameters.theta) * (
                -np.expm1(-parameters.kappa * tau) / (parameters.kappa * tau)
            )
            control_status = "expected_average_variance"
        else:
            aux_first_midpoint = float((times[0] + times[1]) / 2)
            base, status, valid = _local_variance(surface, aux_first_midpoint, np.array([spot]))
            control_variance = float(state * base[0])
            control_status = str(status[0])
            if not valid[0]:
                path_mask[:] = False
                reasons[:] = "unsupported_auxiliary_variance"
    c = np.zeros(paths)
    mu = np.zeros(paths)
    sigma = np.zeros(paths)
    left_spot = np.full(paths, spot, dtype=float)
    left_variance = np.full(paths, state if model == "heston" else np.nan, dtype=float)
    left_coefficient = np.zeros(paths)
    aux_prefix = np.zeros(paths)
    aux_loading = 0.0
    last_z = np.zeros(paths)
    deterministic = True
    for step in range(int(fixings[-1]) if fixings.size else 0):
        dt = float(times[step + 1] - times[step])
        active = np.flatnonzero(path_mask)
        if not active.size:
            break
        zs = normals[active, step, 0]
        zv_independent = normals[active, step, 1]
        last_step = step + 1 == fixings[-1]
        finite_driver = np.isfinite(zs)
        if model == "heston" and not last_step and parameters.xi != 0:
            finite_driver &= np.isfinite(zv_independent)
        if model == "local":
            base, status, supported = _local_variance(
                surface, (times[step] + times[step + 1]) / 2, stock[active]
            )
            old_variance = state * base
            record_status(active, step, status)
        else:
            old_variance = variance[active].copy()
            supported = np.isfinite(old_variance) & (old_variance >= 0)
            record_status(active, step, "heston_left_variance")
        valid = finite_driver & supported
        failed = active[~valid]
        path_mask[failed] = False
        reasons[failed] = np.where(
            finite_driver[~valid], "unsupported_model_variance", "nonfinite_driver"
        )
        active = active[valid]
        if not active.size:
            continue
        old_variance = old_variance[valid]
        zs = zs[valid]
        zv_independent = zv_independent[valid]
        deterministic = deterministic and bool(np.all(old_variance == 0))
        increment_mu = (drift - old_variance / 2) * dt
        increment_sigma = np.sqrt(old_variance * dt)
        aux_mu = (drift - control_variance / 2) * dt
        aux_sigma = np.sqrt(control_variance * dt)
        if step + 1 == fixings[-1]:
            left_spot[active] = stock[active]
            left_variance[active] = old_variance
            left_coefficient[active] = np.sqrt(old_variance)
            c[active] = stock[active] / spot
            mu[active] = increment_mu
            sigma[active] = increment_sigma
            last_z[active] = zs
            aux_prefix[active] = (
                aux_log_sum[active] + aux_log_stock[active] + aux_mu
            ) / fixings.size
            aux_loading = float(aux_sigma / fixings.size)
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            stock[active] *= np.exp(increment_mu + increment_sigma * zs)
            aux_log_stock[active] += aux_mu + aux_sigma * zs
            if model == "heston" and not last_step:
                zv = parameters.rho * zs + np.sqrt(1 - parameters.rho**2) * zv_independent
                variance[active] = cir_implicit_step(variance[active], zv, dt, parameters)
        finite_state = (
            np.isfinite(stock[active]) & (stock[active] > 0) & np.isfinite(variance[active])
        )
        failed = active[~finite_state]
        path_mask[failed] = False
        reasons[failed] = "nonfinite_or_nonpositive_state"
        if step + 1 in fixings:
            if step + 1 != fixings[-1]:
                b[active] += stock[active] / spot
            aux_log_sum[active] += aux_log_stock[active]
    for array in (b, c, mu, sigma, left_spot, left_variance, left_coefficient, aux_prefix, last_z):
        array[~path_mask] = np.nan
    driver_id = hashlib.sha256(np.ascontiguousarray(normals).tobytes()).hexdigest()
    return {
        "model": model,
        "spot": float(spot),
        "state": float(state),
        "memory_count": int(memory_count),
        "total_fixings": 12,
        "calendar_times": times.copy(),
        "fixing_indices": fixings.copy(),
        "fixing_delays": delays.copy(),
        "expiry_delay": expiry_delay,
        "rate": float(parameters.rate),
        "dividend_yield": float(parameters.dividend_yield),
        "original_path_count": paths,
        "N": paths,
        "shared_driver_id": driver_id,
        "shared_driver_scope": "original IID path/step/factor; reuse explicitly across nodes",
        "b": b,
        "c": c,
        "mu": mu,
        "sigma": sigma,
        "last_z": last_z,
        "last_left_spot": left_spot,
        "last_left_variance": left_variance,
        "last_left_coefficient": left_coefficient,
        "aux_logG_prefix": aux_prefix,
        "aux_last_loading": aux_loading,
        "control_variance": control_variance,
        "control_status": control_status,
        "aux_first_midpoint": aux_first_midpoint,
        "path_mask": path_mask,
        "primitive_status": np.where(path_mask, "ready", "invalid"),
        "failure_reasons": reasons,
        "local_step_status": step_status,
        "local_step_status_encoding": "uint8_dictionary" if compact_status else "unicode",
        "local_step_status_labels": np.asarray(status_labels, dtype="<U64")
        if compact_status
        else None,
        "analytic_conditional": bool(fixings.size and fixings[-1] == 1),
        "deterministic_model": bool(deterministic),
        "f_units": "normalized_undiscounted",
    }


def _moments(samples, blocks):
    n = samples.shape[0]
    block_means = samples.reshape(blocks, n // blocks, *samples.shape[1:]).mean(axis=1)
    covariance = (
        np.atleast_2d(np.cov(block_means.reshape(blocks, -1), rowvar=False, ddof=1)) / blocks
    )
    return block_means, covariance


def primitive_labels(primitives: dict, thresholds: np.ndarray, *, blocks: int = 16) -> dict:
    """Replay raw/last-conditioned/beta=1 CV curves and joint IID block errors.

    Means have shape ``(thresholds,)`` and samples ``(original N, thresholds)``.
    ``block_means`` has shape ``(blocks, thresholds, 3)`` in raw/conditioned/CV
    order. Its flattened covariance is covariance of the mean estimator.
    ``f_x_block_means`` uses the same path clusters and threshold derivative of
    the same CV price. No negative CV sample is clipped. Any invalid original
    path makes the whole label unknown, rather than changing its denominator.
    """
    x = np.asarray(thresholds, dtype=float)
    n = primitives["original_path_count"]
    if (
        x.ndim != 1
        or not x.size
        or not np.isfinite(x).all()
        or np.any(np.diff(x) <= 0)
        or not isinstance(blocks, (int, np.integer))
        or blocks < 2
        or n % blocks
    ):
        raise ValueError("increasing finite thresholds and equally sized IID blocks required")
    b, c, mu, sigma, z = [
        np.asarray(primitives[key])[:, None] for key in ("b", "c", "mu", "sigma", "last_z")
    ]
    m = len(primitives["fixing_delays"])
    conditioned = conditional_tail(b, c, mu, sigma, x)
    with np.errstate(over="ignore", invalid="ignore"):
        raw_sum = b + c * np.exp(mu + sigma * z)
        raw = np.maximum(raw_sum - x, 0)
        aux_c = m * np.exp(np.asarray(primitives["aux_logG_prefix"])[:, None])
        aux_raw_sum = aux_c * np.exp(primitives["aux_last_loading"] * z)
        aux_raw = np.maximum(aux_raw_sum - x, 0)
    aux = conditional_tail(0, aux_c, 0, primitives["aux_last_loading"], x)
    known_mu, known_sigma = _geometric_law(
        primitives["control_variance"],
        primitives["fixing_delays"],
        primitives["rate"] - primitives["dividend_yield"],
    )
    known = conditional_tail(0, m, known_mu, known_sigma, x)
    cv = conditioned["f"] - aux["f"] + known["f"]
    cv_x = conditioned["f_x"] - aux["f_x"] + known["f_x"]
    raw_x = np.where(np.isfinite(raw_sum), -(raw_sum > x).astype(float), np.nan)
    invalid_paths = ~np.asarray(primitives["path_mask"], dtype=bool)
    for derivative in (raw_x, conditioned["f_x"], cv_x):
        derivative[invalid_paths] = np.nan
    raw_cv = cv.copy()
    raw_cv_x = cv_x.copy()
    all_valid = bool(np.all(primitives["path_mask"]))
    linear = x <= 0 if m else x < 0
    exact_sum = np.exp(
        (primitives["rate"] - primitives["dividend_yield"]) * primitives["fixing_delays"]
    ).sum()
    if all_valid:
        cv[:, linear] = exact_sum - x[linear]
        cv_x[:, linear] = -1
    samples = np.stack([raw, conditioned["f"], cv], axis=-1)
    derivative_samples = np.stack(
        [
            raw_x,
            conditioned["f_x"],
            cv_x,
        ],
        axis=-1,
    )
    block_means, block_covariance = _moments(samples, blocks)
    derivative_blocks, derivative_covariance = _moments(derivative_samples, blocks)
    joint = np.concatenate([samples.reshape(n, -1), derivative_samples.reshape(n, -1)], axis=1)
    joint_blocks, joint_covariance = _moments(joint, blocks)
    with np.errstate(invalid="ignore"):
        means = samples.mean(axis=0)
        se = samples.std(axis=0, ddof=1) / np.sqrt(n)
        derivative_means = derivative_samples.mean(axis=0)
        derivative_se = derivative_samples.std(axis=0, ddof=1) / np.sqrt(n)
    f = means[:, 2].copy()
    fx = derivative_means[:, 2].copy()
    f_se = se[:, 2].copy()
    fx_se = derivative_se[:, 2].copy()
    statuses = np.full(x.shape, "ready", dtype="<U40")
    if not all_valid:
        statuses[:] = "unknown_invalid_primitives"
        f[:] = fx[:] = f_se[:] = fx_se[:] = np.nan
    else:
        bad = ~np.isfinite(f) | ~np.isfinite(f_se)
        statuses[bad] = "unknown_nonfinite_label"
        atom = (
            np.any(conditioned["status"] == "unknown_atom", axis=0)
            | np.any(aux["status"] == "unknown_atom", axis=0)
            | (known["status"] == "unknown_atom")
        )
        statuses[atom] = "unknown_atom"
        underresolved = (
            ((f_se == 0) | np.all(cv == cv[0], axis=0) | np.all(conditioned["f"] == 0, axis=0))
            & ~bad
            & ~atom
        )
        if not (primitives["analytic_conditional"] or primitives["deterministic_model"]):
            statuses[underresolved] = "unknown_underresolved"
            derivative_underresolved = (fx_se == 0) | np.all(cv_x == cv_x[0], axis=0)
            statuses[derivative_underresolved & ~bad & ~atom] = "unknown_underresolved"
        if not primitives["deterministic_model"]:
            allzero = np.all(conditioned["f"] == 0, axis=0)
            statuses[allzero & ~bad & ~atom] = "unknown_underresolved"
        # x<=0 is exactly linear under Q for positive stock, independent of
        # auxiliary geometric memory. Override only the qualified price curve.
        f[linear] = exact_sum - x[linear]
        fx[linear] = -1
        f_se[linear] = fx_se[linear] = 0
        statuses[linear] = "not_required_linear_claim"
        if not m:
            non_atom = x != 0
            f[non_atom] = np.maximum(-x[non_atom], 0)
            fx[non_atom] = -(x[non_atom] < 0).astype(float)
            f_se[non_atom] = fx_se[non_atom] = 0
            statuses[non_atom] = "not_required_settled_claim"
    result = {
        key: primitives[key]
        for key in (
            "spot",
            "state",
            "model",
            "memory_count",
            "total_fixings",
            "fixing_delays",
            "calendar_times",
            "fixing_indices",
            "expiry_delay",
            "rate",
            "dividend_yield",
            "original_path_count",
            "N",
            "shared_driver_id",
            "shared_driver_scope",
            "f_units",
        )
    }
    result.update(
        {
            "thresholds": x.copy(),
            "f": f,
            "f_x": fx,
            "f_se": f_se,
            "f_x_se": fx_se,
            "status": statuses,
            "status_reasons": statuses.copy(),
            "raw_samples": raw,
            "conditioned_samples": conditioned["f"],
            "cv_samples": cv,
            "f_samples": cv,
            "f_x_samples": cv_x,
            "raw_x_samples": raw_x,
            "conditioned_x_samples": conditioned["f_x"],
            "unreplaced_cv_samples": raw_cv,
            "unreplaced_cv_x_samples": raw_cv_x,
            "aux_raw_samples": aux_raw,
            "aux_conditioned_samples": aux["f"],
            "aux_mean": known["f"],
            "aux_mean_x": known["f_x"],
            "component_order": ("raw", "conditioned", "cv"),
            "component_means": means,
            "component_se": se,
            "derivative_component_means": derivative_means,
            "derivative_component_se": derivative_se,
            "blocks": blocks,
            "block_path_count": n // blocks,
            "block_means": block_means,
            "block_covariance": block_covariance,
            "f_x_block_means": derivative_blocks[:, :, 2],
            "derivative_block_means": derivative_blocks,
            "derivative_block_covariance": derivative_covariance,
            "joint_block_means": joint_blocks,
            "joint_block_covariance": joint_covariance,
            "joint_order": "flatten(threshold,component price), then flatten(threshold,component derivative)",
            "path_mask": np.asarray(primitives["path_mask"]).copy(),
        }
    )
    return result
