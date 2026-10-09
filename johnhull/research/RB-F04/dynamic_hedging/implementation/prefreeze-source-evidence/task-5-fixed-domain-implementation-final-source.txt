"""Private calendar call / normalized Asian C1 caches for dynamic RB-F04.

Times are years, prices currency, spot derivatives stock units, and state
derivatives currency per annual variance (Heston) or multiplier (local).
Every interpolated axis uses the same linear not-a-knot cubic operator.
No extrapolation, price clipping, nearest-root substitution, or fixing-time
interpolation is performed. Explicit Asian evaluation boxes use the same C2
operator on fixed subaxes; no continuity across unknown gaps is asserted.
Numerical accuracy remains a measured pilot gate.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import replace
from functools import lru_cache

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq
from scipy.sparse import diags
from scipy.sparse.linalg import splu

from ._heston_local_surface import HestonParameters, fourier_surface


def _axis(values, name, *, positive=False, cubic=True):
    axis = np.asarray(values, dtype=float)
    if (
        axis.ndim != 1
        or axis.size < (4 if cubic else 1)
        or np.any(~np.isfinite(axis))
        or np.any(np.diff(axis) <= 0)
        or (positive and np.any(axis <= 0))
    ):
        raise ValueError(
            f"{name} requires finite increasing {'four or more' if cubic else ''} nodes"
        )
    return axis.copy()


def _model(model):
    if model not in {"heston", "local"}:
        raise ValueError("model must be heston or local")


def _date(cache, date_index):
    return (
        isinstance(date_index, (int, np.integer))
        and not isinstance(date_index, bool)
        and 0 <= date_index < len(cache["dates"])
    )


@lru_cache(maxsize=128)
def _basis(nodes):
    return CubicSpline(np.array(nodes), np.eye(len(nodes)), axis=0, extrapolate=False)


def _tensor(values, axes, point, derivative=None):
    result = np.asarray(values, dtype=float)
    for i, (axis, coordinate) in enumerate(zip(axes, point, strict=True)):
        weights = _basis(tuple(axis))(coordinate, 1 if derivative == i else 0)
        result = np.tensordot(weights, result, axes=(0, 0))
    return result


def _unknown(reason, **diagnostics):
    return {
        "value": np.nan,
        "spot_derivative": np.nan,
        "state_derivative": np.nan,
        "status": "unknown",
        "reason": reason,
        "error": np.nan,
        **diagnostics,
    }


def _batch_results(rows, shape):
    """Keep numeric arrays numeric; pad variable root diagnostics with NaN."""
    result = {}
    for key in set().union(*(row.keys() for row in rows)):
        example = next(row[key] for row in rows if key in row)
        if isinstance(example, str):
            result[key] = np.asarray([row.get(key, "") for row in rows]).reshape(shape)
            continue
        arrays = [np.asarray(row.get(key, np.nan), float) for row in rows]
        ndim = max(a.ndim for a in arrays)
        tail = tuple(max(a.shape[i] if a.ndim == ndim else 0 for a in arrays) for i in range(ndim))
        output = np.full((len(rows), *tail), np.nan)
        for j, a in enumerate(arrays):
            if a.ndim == ndim:
                output[(j, *tuple(slice(0, k) for k in a.shape))] = a
        result[key] = output.reshape(shape + tail)
    return result


def _calendar_pde(
    parameters,
    surface,
    dates,
    ell,
    spot_nodes,
    *,
    space_nodes=1201,
    time_steps=960,
    log_half_width=1.8,
    strike=100.0,
    maturity=1.25,
):
    """One sparse CN/Rannacher solve per ell, with exact calendar snapshots.

    The 1201-node spatial default resolves the late ATM call to the initial
    0.001 price budget in the independent Black/actual-field probes. This
    measured comparison does not certify other states or derivative errors.
    """
    x = np.linspace(
        math.log(parameters.spot) - log_half_width,
        math.log(parameters.spot) + log_half_width,
        space_nodes,
    )
    stocks = np.exp(x)
    if spot_nodes[0] < stocks[0] or spot_nodes[-1] > stocks[-1]:
        raise ValueError("requested spot nodes must lie in the PDE domain")
    r, q = parameters.rate, parameters.dividend_yield
    if (
        stocks[0] * math.exp(max(0.0, (r - q) * maturity)) > strike
        or stocks[-1] * math.exp(min(0.0, (r - q) * maturity)) < strike
    ):
        return np.full((len(dates), len(spot_nodes)), np.nan), {"failure": "unsupported_domain"}
    # Union makes every saved date an actual time-step endpoint.
    timeline = np.unique(np.r_[np.linspace(0.0, maturity, time_steps + 1), dates])[::-1]
    value = np.maximum(stocks - strike, 0.0)
    snapshots = {}
    counts = {}
    evaluation_times = []
    dx = x[1] - x[0]
    failure = None
    negative_coefficients = 0
    for step, (right, left) in enumerate(itertools.pairwise(timeline)):
        subintervals = (
            [(right, (right + left) / 2), ((right + left) / 2, left)]
            if step == 0
            else [(right, left)]
        )
        weight = 1.0 if step == 0 else 0.5
        for end, start in subintervals:
            dt = end - start
            t = (end + start) / 2
            evaluation_times.append(t)
            coefficient = surface.evaluate(t, stocks[1:-1])
            var = np.broadcast_to(coefficient["variance"], stocks[1:-1].shape) * ell
            statuses = np.broadcast_to(coefficient["status"], var.shape).astype(str)
            labels, number = np.unique(statuses, return_counts=True)
            for label, count in zip(labels, number, strict=True):
                counts[label] = counts.get(label, 0) + int(count)
            if (
                np.any(~np.isfinite(var))
                or np.any(var < 0)
                or np.any(np.char.startswith(statuses, "unsupported"))
            ):
                failure = "unsupported_variance"
                break
            low = 0.5 * var / dx**2 - (r - q - 0.5 * var) / (2 * dx)
            middle = -var / dx**2 - r
            high = 0.5 * var / dx**2 + (r - q - 0.5 * var) / (2 * dx)
            negative_coefficients += int(np.count_nonzero(low < 0) + np.count_nonzero(high < 0))
            rhs = value[1:-1] + (1 - weight) * dt * (
                low * value[:-2] + middle * value[1:-1] + high * value[2:]
            )
            upper = stocks[-1] * math.exp(-q * (maturity - start)) - strike * math.exp(
                -r * (maturity - start)
            )
            rhs[-1] += weight * dt * high[-1] * upper
            operator = diags(
                (-weight * dt * low[1:], 1 - weight * dt * middle, -weight * dt * high[:-1]),
                [-1, 0, 1],
                format="csc",
            )
            value = np.r_[0.0, splu(operator).solve(rhs), upper]
            if np.any(~np.isfinite(value)):
                failure = "nonfinite_solution"
                break
        if failure:
            break
        if np.any(dates == left):
            snapshots[float(left)] = CubicSpline(x, value)(np.log(spot_nodes))
    result = np.stack([snapshots.get(float(t), np.full(len(spot_nodes), np.nan)) for t in dates])
    return result, {
        "failure": failure,
        "status_counts": counts,
        "coefficient_min_time": min(evaluation_times, default=np.nan),
        "coefficient_max_time": max(evaluation_times, default=np.nan),
        "negative_operator_coefficients": negative_coefficients,
        "space_nodes": space_nodes,
        "time_steps": len(timeline) - 1,
        "log_half_width": log_half_width,
    }


def build_call_cache(parameters, surface, *, dates, spot_nodes, state_nodes, model):
    """Build K100/T1.25 calls using current v CF or absolute-calendar local PDE.

    ``parameters`` is the approved ``HestonParameters``; ``surface`` is
    ``LocalVarianceGrid`` for local. Small axes are supported for fixtures;
    four nodes per cubic axis are mandatory. Raw values and solver diagnostics
    are retained. Reference error is NaN until measured independently.
    """
    _model(model)
    if not isinstance(parameters, HestonParameters):
        raise ValueError("parameters must be HestonParameters")
    dates = _axis(dates, "dates", cubic=False)
    spots = _axis(spot_nodes, "spot", positive=True)
    states = _axis(state_nodes, "state", positive=True)
    if dates[0] < 0 or dates[-1] >= 1.25:
        raise ValueError("call dates must be in [0,1.25)")
    values = np.empty((len(dates), len(spots), len(states)))
    diagnostics = []
    if model == "heston":
        for j, t in enumerate(dates):
            for k, s in enumerate(spots):
                for l, v in enumerate(states):
                    p = replace(parameters, spot=float(s), v0=float(v))
                    values[j, k, l] = fourier_surface(np.array([100.0]), 1.25 - t, p)["price"][0]
        diagnostics.append({"method": "heston_cf", "order": 1024, "maturities": 1.25 - dates})
    else:
        if surface is None or not callable(getattr(surface, "evaluate", None)):
            raise ValueError("local requires LocalVarianceGrid.evaluate")
        for l, ell in enumerate(states):
            values[:, :, l], diagnostic = _calendar_pde(parameters, surface, dates, ell, spots)
            diagnostics.append(diagnostic)
    return {
        "model": model,
        "dates": dates,
        "spot_nodes": spots,
        "state_nodes": states,
        "values": values,
        "rate": parameters.rate,
        "dividend_yield": parameters.dividend_yield,
        "strike": 100.0,
        "maturity": 1.25,
        "price_error": np.nan,
        "derivative_error": np.nan,
        "diagnostics": diagnostics,
        "support_mask": np.isfinite(values),
        "coefficient_min_times": np.array(
            [d.get("coefficient_min_time", np.nan) for d in diagnostics]
        ),
        "interpolation": "not_a_knot_tensor_cubic",
        "reference_status": "unmeasured",
    }


def evaluate_call(cache: dict, date_index: int, spot, state) -> dict:
    """Evaluate a saved call date and both ordinary derivatives of its price spline."""
    if not _date(cache, date_index):
        return _unknown("date_index")
    spot, state = np.broadcast_arrays(np.asarray(spot, float), np.asarray(state, float))
    if spot.ndim:
        rows = [
            evaluate_call(cache, date_index, s, v)
            for s, v in zip(spot.flat, state.flat, strict=True)
        ]
        return _batch_results(rows, spot.shape)
    axes = [np.asarray(cache["spot_nodes"]), np.asarray(cache["state_nodes"])]
    if not np.isfinite(spot + state) or any(
        v < a[0] or v > a[-1] for a, v in zip(axes, [spot, state], strict=True)
    ):
        return _unknown("outside_support")
    values = cache["values"][date_index]
    if np.any(~np.isfinite(values)):
        return _unknown("nonfinite_nodes")
    point = [float(spot), float(state)]
    value = float(_tensor(values, axes, point))
    ds = float(_tensor(values, axes, point, 0))
    dv = float(_tensor(values, axes, point, 1))
    tau = cache["maturity"] - cache["dates"][date_index]
    upper = float(spot) * math.exp(-cache["dividend_yield"] * tau)
    lower = max(upper - cache["strike"] * math.exp(-cache["rate"] * tau), 0.0)
    if not np.isfinite(value + ds + dv) or value < lower - 1e-10 or value > upper + 1e-10:
        return _unknown(
            "price_bounds", raw_value=value, raw_spot_derivative=ds, raw_state_derivative=dv
        )
    return {
        "value": value,
        "spot_derivative": ds,
        "state_derivative": dv,
        "status": "ok",
        "reason": "",
        "error": cache.get("price_error", np.nan),
    }


def normalized_price_greeks(
    spot, discount, threshold, f, f_x, f_state, *, model, state, f_log_spot=0.0
) -> dict:
    """Apply the Asian chain rule (12 fixings); local f_state is d f/d log ell."""
    _model(model)
    s, d, x, f, fx, fs, v, fz = np.broadcast_arrays(
        spot, discount, threshold, f, f_x, f_state, state, f_log_spot
    )
    if np.any(s <= 0) or np.any(d <= 0) or (model == "local" and np.any(v <= 0)):
        raise ValueError("positive spot/discount/local multiplier required")
    return {
        "value": d * s * f / 12,
        "spot_derivative": d * (f - x * fx + (fz if model == "local" else 0.0)) / 12,
        "state_derivative": d * s * fs / (12 * v if model == "local" else 12.0),
    }


def _asian_evaluation_domains(domains, model, dates, states, threshold, spots, t0_spots):
    """Snapshot per-date contiguous node boxes, independent of query or labels."""
    if not isinstance(domains, (list, tuple)) or len(domains) != len(dates):
        raise ValueError("evaluation domain requires one explicit entry per exact date")
    names = (["spot"] if model == "local" else []) + ["state", "threshold"]
    snapshots, bounds, sheets = [], [], []
    for j, domain in enumerate(domains):
        sheet = "t0_sheet" if model == "local" and dates[j] == 0 else "main"
        sheets.append(sheet)
        if domain is None:
            snapshots.append(None)
            bounds.append(None)
            continue
        if not isinstance(domain, dict) or set(domain) != set(names):
            raise ValueError("evaluation domain must declare exactly the model's cubic axes")
        axes = {"state": states, "threshold": threshold[j]}
        if model == "local":
            axes["spot"] = t0_spots if sheet == "t0_sheet" else spots
        copied, endpoints = {}, {}
        for name in names:
            interval = domain[name]
            if (
                not isinstance(interval, (list, tuple))
                or len(interval) != 2
                or any(
                    not isinstance(k, (int, np.integer)) or isinstance(k, bool) for k in interval
                )
            ):
                raise ValueError("evaluation domain requires integer half-open node ranges")
            a, b = (int(k) for k in interval)
            if a < 0 or b > len(axes[name]) or b - a < 4:
                raise ValueError("evaluation domain needs four or more contiguous original nodes")
            copied[name] = [a, b]
            endpoints[name] = [float(axes[name][a]), float(axes[name][b - 1])]
        snapshots.append(copied)
        bounds.append(endpoints)
    return {
        "evaluation_domains": snapshots,
        "evaluation_domain_schema": "rb-f04-asian-fixed-domain-v1",
        "evaluation_domain_bounds": bounds,
        "evaluation_domain_sheets": sheets,
    }


def build_asian_cache(
    primitive_groups: dict, *, model: str, axes: dict, evaluation_domains=None
) -> dict:
    """Construct exact-date normalized CV tables with shared IID block curves.

    Axes are ``dates``, ``state``, ``threshold`` (1D or per-date 2D), and
    ``spot`` for local. The production input has ``groups`` containing Task2
    label dictionaries plus ``date_index``. Every Cartesian node is required;
    unavailable/failed nodes remain NaN. A dense ``f``/``block_means`` input
    uses shape (date,[spot],state,threshold,[16,3]) for analytic fixtures.
    Heston has no spot axis: its normalized claim is homogeneous. Local axes
    use log S/log ell internally; price and derivatives share that operator.

    evaluation_domains=None preserves the original global operator. An
    explicit per-date list declares one fixed box or None (unavailable).
    Each box maps its cubic axes to half-open contiguous original node index
    ranges, with four or more nodes per axis. Local date-zero spot indices
    refer to the dedicated t0 sheet. Only evaluation is restricted: full
    arrays, primitive statuses, IID blocks and original N remain unchanged.
    Availability is not a financial precision qualification.
    """
    _model(model)
    dates = _axis(axes["dates"], "dates", cubic=False)
    states = _axis(axes["state"], "state", positive=True)
    threshold = np.asarray(axes["threshold"], float)
    if threshold.ndim == 1:
        threshold = np.broadcast_to(threshold, (len(dates), len(threshold))).copy()
    if threshold.ndim != 2 or threshold.shape[0] != len(dates):
        raise ValueError("threshold requires one axis per exact date")
    for x in threshold:
        _axis(x, "threshold")
    shape = (len(dates),)
    spots = None
    if model == "local":
        spots = _axis(axes["spot"], "spot", positive=True)
        shape += (len(spots),)
    shape += (len(states), threshold.shape[1])
    t0_sheet = None
    t0_spots = (
        _axis(axes["t0_spot"], "t0_spot", positive=True)
        if model == "local" and "t0_spot" in axes
        else spots
    )
    original_n = primitive_groups.get("N")
    driver_ids = set()
    if "groups" in primitive_groups:
        f = np.full(shape, np.nan)
        blocks = np.full((*shape, 16, 3), np.nan)
        seen = set()
        if model == "local" and dates[0] == 0:
            if "t0_spot" not in axes:
                raise ValueError("local production groups require a dedicated t0_spot axis")
            t0_shape = (len(t0_spots), len(states), threshold.shape[1])
            t0_sheet = {
                "spot_nodes": t0_spots,
                "f": np.full(t0_shape, np.nan),
                "block_means": np.full((*t0_shape, 16, 3), np.nan),
            }
        for group in primitive_groups["groups"]:
            j = group["date_index"]
            if not isinstance(j, (int, np.integer)) or j < 0 or j >= len(dates):
                raise ValueError("group date_index must match dates")
            if (
                group["memory_count"] != math.floor(dates[j] * 12 + 1e-9)
                or abs(group["calendar_times"][0] - dates[j]) > 1e-12
            ):
                raise ValueError("group memory/calendar restart must match the exact cache date")
            denominator = group["N"]
            if (
                not isinstance(denominator, (int, np.integer))
                or denominator < 16
                or denominator % 16
            ):
                raise ValueError("each original denominator must be a positive multiple of 16")
            if original_n is None:
                original_n = int(denominator)
            if denominator != original_n:
                raise ValueError("all shared node curves require the same original denominator")
            driver_ids.add(group["shared_driver_id"])
            if len(driver_ids) > 1:
                raise ValueError("node curves must share the declared CRN driver")
            state_index = np.flatnonzero(states == group["state"])
            group_spots = t0_spots if model == "local" and dates[j] == 0 else spots
            spot_index = (
                np.flatnonzero(group_spots == group["spot"]) if spots is not None else np.array([0])
            )
            if (
                len(state_index) != 1
                or len(spot_index) != 1
                or not np.array_equal(group["thresholds"], threshold[j])
            ):
                raise ValueError("group state/spot/thresholds must exactly match cache axes")
            index = (
                (j, int(spot_index[0]), int(state_index[0]))
                if model == "local"
                else (j, int(state_index[0]))
            )
            if index in seen:
                raise ValueError("duplicate Cartesian group")
            seen.add(index)
            curve = np.asarray(group["f"], float).copy()
            block = np.moveaxis(group["block_means"], 0, 1).copy()
            statuses = np.asarray(group["status"]).astype(str)
            unavailable = np.char.startswith(statuses, "unknown")
            curve[unavailable], block[unavailable] = np.nan, np.nan
            if t0_sheet is not None and dates[j] == 0:
                t0_sheet["f"][index[1:]] = curve
                t0_sheet["block_means"][index[1:]] = block
            else:
                f[index], blocks[index] = curve, block
    else:
        f = np.asarray(primitive_groups["f"], float).copy()
        blocks = np.asarray(
            primitive_groups.get("block_means", np.full((*shape, 16, 3), np.nan)), float
        ).copy()
        if model == "local" and dates[0] == 0:
            t0_f = np.asarray(primitive_groups.get("t0_f", f[0]), float)
            t0_block = np.asarray(primitive_groups.get("t0_block_means", blocks[0]), float)
            if t0_f.shape != (len(t0_spots), len(states), threshold.shape[1]) or t0_block.shape != (
                *t0_f.shape,
                16,
                3,
            ):
                raise ValueError("dedicated t0 curves must match t0_spot/state/threshold/16x3 axes")
            t0_sheet = {"spot_nodes": t0_spots, "f": t0_f.copy(), "block_means": t0_block.copy()}
    if f.shape != shape or blocks.shape != (*shape, 16, 3):
        raise ValueError("normalized curves/block curves must match Cartesian axes and 16x3 blocks")
    p = primitive_groups.get("parameters")
    if not isinstance(p, HestonParameters):
        raise ValueError("primitive_groups.parameters must be HestonParameters")
    counts = np.floor(dates * 12 + 1e-9).astype(int)
    if dates[0] < 0 or dates[-1] >= 1 or np.any(counts > 11):
        raise ValueError("Asian cache dates must be in [0,1)")
    cache = {
        "model": model,
        "dates": dates,
        "state_nodes": states,
        "spot_nodes": spots,
        "threshold_nodes": threshold,
        "f": f,
        "block_means": blocks,
        "memory_counts": counts,
        "rate": p.rate,
        "dividend_yield": p.dividend_yield,
        "strike": 100.0,
        "maturity": 1.0,
        "primitive_groups": primitive_groups,
        "original_N": original_n,
        "support_mask": np.isfinite(f),
        "interpolation": "not_a_knot_tensor_cubic",
        "shared_driver_ids": tuple(driver_ids),
        "t0_sheet": t0_sheet,
    }
    if evaluation_domains is not None:
        cache.update(
            _asian_evaluation_domains(
                evaluation_domains, model, dates, states, threshold, spots, t0_spots
            )
        )
    return cache


def evaluate_asian(cache: dict, date_index: int, spot, state, memory_sum, memory_count) -> dict:
    """Value the monthly Asian from one fixed same-price interpolation domain.

    Exact linear/settled branches require no patch or fitted state. Explicit
    boxes use common subaxes for mean and all sixteen CV block curves; unknown
    nodes outside the box are retained, while necessary unavailable nodes
    make this date unknown. Box boundaries use only the inward derivative,
    without extrapolation or a continuity claim across unsupported gaps.
    """
    if not _date(cache, date_index):
        return _unknown("date_index")
    spot, state, a, n = np.broadcast_arrays(
        np.asarray(spot, float),
        np.asarray(state, float),
        np.asarray(memory_sum, float),
        np.asarray(memory_count, float),
    )
    if spot.ndim:
        rows = [
            evaluate_asian(cache, date_index, s, v, aa, nn)
            for s, v, aa, nn in zip(spot.flat, state.flat, a.flat, n.flat, strict=True)
        ]
        return _batch_results(rows, spot.shape)
    if not np.isfinite(spot + a + n) or spot <= 0 or n != int(n) or n < 0 or n > 12 or a < 0:
        return _unknown("invalid_memory")
    if n == 12:
        return {
            "value": max(float(a) / 12 - cache["strike"], 0.0),
            "spot_derivative": 0.0,
            "state_derivative": 0.0,
            "status": "not_required_settled_claim",
            "reason": "",
            "error": 0.0,
        }
    if n != cache["memory_counts"][date_index]:
        return _unknown("memory_date_mismatch")
    t = cache["dates"][date_index]
    d = math.exp(-cache["rate"] * (1 - t))
    x = (12 * cache["strike"] - float(a)) / float(spot)
    if x <= 0:
        delays = np.arange(int(n) + 1, 13) / 12 - t
        expected_sum = np.exp((cache["rate"] - cache["dividend_yield"]) * delays).sum()
        return {
            "value": d * (float(a) + float(spot) * expected_sum - 12 * cache["strike"]) / 12,
            "spot_derivative": d * expected_sum / 12,
            "state_derivative": 0.0,
            "status": "not_required_linear_claim",
            "reason": "",
            "error": 0.0,
        }
    local = cache["model"] == "local"
    sheet = cache.get("t0_sheet") if local and t == 0 else None
    interpolation_spots = sheet["spot_nodes"] if sheet is not None else cache["spot_nodes"]
    if sheet is not None and (spot < interpolation_spots[0] or spot > interpolation_spots[-1]):
        return _unknown("outside_t0_support")
    axes = [np.log(interpolation_spots)] if local else []
    axes += [
        np.log(cache["state_nodes"]) if local else cache["state_nodes"],
        cache["threshold_nodes"][date_index],
    ]
    if not np.isfinite(state) or state <= 0:
        return _unknown("outside_support")
    point = [math.log(float(spot))] if local else []
    point += [math.log(float(state)) if local else float(state), x]
    if any(v < axis[0] or v > axis[-1] for axis, v in zip(axes, point, strict=True)):
        return _unknown("outside_support")
    values = sheet["f"] if sheet is not None else cache["f"][date_index]
    blocks = None
    future_mean = np.exp(
        (cache["rate"] - cache["dividend_yield"]) * (np.arange(int(n) + 1, 13) / 12 - t)
    ).sum()
    domains = cache.get("evaluation_domains")
    if domains is not None:
        domain = domains[date_index]
        if domain is None:
            return _unknown("no_evaluation_domain")
        names = (["spot"] if local else []) + ["state", "threshold"]
        slices = tuple(slice(*domain[name]) for name in names)
        axes = [axis[section] for axis, section in zip(axes, slices, strict=True)]
        if any(v < axis[0] or v > axis[-1] for axis, v in zip(axes, point, strict=True)):
            return _unknown("outside_evaluation_domain")
        values = values[slices]
        if np.any(~np.isfinite(values)):
            return _unknown("nonfinite_domain_nodes")
        blocks = (sheet["block_means"] if sheet is not None else cache["block_means"][date_index])[
            ..., 2
        ][slices]
        if np.any(~np.isfinite(blocks)):
            return _unknown("nonfinite_domain_blocks")
        if np.any(values < -1e-12) or np.any(values > future_mean + 1e-12):
            return _unknown(
                "domain_price_bounds",
                raw_min_f=float(np.min(values)),
                raw_max_f=float(np.max(values)),
            )
    elif np.any(~np.isfinite(values)):
        return _unknown("nonfinite_nodes")
    f = float(_tensor(values, axes, point))
    fx = float(_tensor(values, axes, point, len(axes) - 1))
    fs = float(_tensor(values, axes, point, int(local)))
    fz = float(_tensor(values, axes, point, 0)) if local else 0.0
    got = normalized_price_greeks(
        float(spot), d, x, f, fx, fs, model=cache["model"], state=float(state), f_log_spot=fz
    )
    if f < -1e-12 or f > future_mean + 1e-12 or fx > 1e-10 or fx < -1 - 1e-10:
        return _unknown("price_bounds", raw_value=float(got["value"]), raw_f=f, raw_f_x=fx)
    if blocks is None:
        blocks = (sheet["block_means"] if sheet is not None else cache["block_means"][date_index])[
            ..., 2
        ]
    fb = _tensor(blocks, axes, point)
    fxb = _tensor(blocks, axes, point, len(axes) - 1)
    fsb = _tensor(blocks, axes, point, int(local))
    fzb = _tensor(blocks, axes, point, 0) if local else 0.0
    block_greeks = normalized_price_greeks(
        float(spot), d, x, fb, fxb, fsb, model=cache["model"], state=float(state), f_log_spot=fzb
    )
    block_values = np.stack(list(block_greeks.values()), axis=-1)
    covariance = np.cov(block_values, rowvar=False, ddof=1) / 16
    return {
        **{k: float(v) for k, v in got.items()},
        "status": "ok",
        "reason": "",
        "error": np.nan,
        "block_values": block_values,
        "covariance": covariance,
        "standard_errors": np.sqrt(np.diag(covariance)),
    }


def fit_quote_state(cache: dict, date_index: int, spot, quote, *, state_scale: float) -> dict:
    """Enumerate all cubic-piece roots/extrema, accepting a unique interior root.

    ``asian_state_bounds`` must be attached by the joint-cache caller to enforce
    the call/Asian support intersection. The returned condition is the state
    move from a one-cent quote bump divided by ``state_scale``. Unknown states
    remain NaN, with raw roots, residual and denominator saved where available.
    """
    fail = {
        "state": np.nan,
        "root": np.nan,
        "residual": np.nan,
        "Ctheta": np.nan,
        "condition": np.nan,
        "status": "unknown",
        "reason": "",
        "roots": np.array([]),
    }
    spot, quote = np.broadcast_arrays(np.asarray(spot, float), np.asarray(quote, float))
    if spot.ndim:
        rows = [
            fit_quote_state(cache, date_index, float(s), float(q), state_scale=state_scale)
            for s, q in zip(spot.flat, quote.flat, strict=True)
        ]
        return _batch_results(rows, spot.shape)
    if not _date(cache, date_index):
        return {**fail, "reason": "date_index"}
    if not np.isfinite(state_scale) or state_scale <= 0:
        raise ValueError("state_scale must be finite and positive")
    if not np.isfinite(spot + quote):
        return {**fail, "reason": "nonfinite_quote"}
    spots, states = np.asarray(cache["spot_nodes"]), np.asarray(cache["state_nodes"])
    if spot < spots[0] or spot > spots[-1]:
        return {**fail, "reason": "outside_support"}
    low, high = states[0], states[-1]
    if "asian_state_bounds" in cache:
        low = max(low, cache["asian_state_bounds"][0])
        high = min(high, cache["asian_state_bounds"][1])
    if low >= high or np.any(~np.isfinite(cache["values"][date_index])):
        return {**fail, "reason": "outside_support"}
    values = _basis(tuple(spots))(spot) @ cache["values"][date_index]
    curve = CubicSpline(states, values, extrapolate=False)
    extrema = curve.derivative().roots(extrapolate=False)
    extrema = extrema[np.isfinite(extrema) & (extrema >= low) & (extrema <= high)]
    roots = curve.solve(float(quote), extrapolate=False)
    finite_roots = np.sort(
        roots[np.isfinite(roots) & (roots >= low - 1e-10) & (roots <= high + 1e-10)]
    )
    unique = []
    for root in finite_roots:
        if not unique or abs(root - unique[-1]) > 1e-8:
            unique.append(float(root))
    fail.update(
        roots=np.array(unique),
        extrema=extrema,
        extrema_values=curve(np.r_[low, extrema, high]),
        state_bounds=np.array([low, high]),
    )
    if np.any(np.isnan(roots)) or len(unique) > 1:
        return {**fail, "reason": "nonunique"}
    if not unique:
        return {**fail, "reason": "no_root"}
    root = unique[0]
    # All pieces were inspected above; refine only this isolated root in a
    # scaled monotone bracket. A tangential root is retained for the low-J gate.
    critical_points = np.unique(np.r_[low, states[(states > low) & (states < high)], extrema, high])
    if low < root < high:
        for left, right in itertools.pairwise(critical_points):
            if left <= root <= right and (curve(left) - quote) * (curve(right) - quote) < 0:
                try:
                    root = state_scale * brentq(
                        lambda u: float(curve(u * state_scale) - quote),
                        left / state_scale,
                        right / state_scale,
                        xtol=1e-10,
                        rtol=1e-10,
                        maxiter=100,
                    )
                except (RuntimeError, ValueError):
                    return {**fail, "reason": "solver_failure"}
                break
    residual = float(curve(root) - quote)
    jacobian = float(curve(root, 1))
    condition = 0.01 / abs(jacobian * state_scale) if jacobian else np.inf
    fail.update(root=root, residual=residual, Ctheta=jacobian, condition=condition)
    if abs(root - low) <= 1e-9 or abs(root - high) <= 1e-9:
        return {**fail, "reason": "bound"}
    if not np.isfinite(jacobian) or condition > 0.25:
        return {**fail, "reason": "ill_conditioned"}
    error = cache.get("derivative_error", np.nan)
    if np.ndim(error):
        error = float(np.nanmax(error))
    if np.isfinite(error) and abs(jacobian) <= 3 * error:
        return {**fail, "reason": "derivative_uncertainty"}
    if abs(residual) > 1e-10 * max(1.0, abs(quote)):
        return {**fail, "reason": "solver_residual"}
    evaluation = evaluate_call(cache, date_index, spot, root)
    if evaluation["status"] != "ok":
        return {**fail, "reason": evaluation["reason"]}
    return {
        **fail,
        "state": root,
        "status": "ok",
        "reason": "",
        "CS": evaluation["spot_derivative"],
        "derivative_error": error,
        "reference_status": cache.get("reference_status", "unmeasured"),
    }
